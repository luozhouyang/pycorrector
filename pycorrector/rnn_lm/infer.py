# -*- coding: utf-8 -*-
# Author: XuMing <xuming624@qq.com>
# Brief:
import numpy as np
import tensorflow as tf

import rnn_lm_config as conf
from rnn_lm.data_reader import UNK_TOKEN, END_TOKEN, START_TOKEN, load_word_dict
from rnn_lm_model import rnn_model


def to_word(predict, vocabs):
    t = np.cumsum(predict)
    s = np.sum(predict)
    sample = int(np.searchsorted(t, np.random.rand(1) * s))
    if sample > len(vocabs):
        sample = 0
    return vocabs[sample]


def generate(begin_word):
    batch_size = 1
    word_to_int = load_word_dict(conf.word_dict_path)
    vocabularies = [k for k, v in word_to_int.items()]
    input_data = tf.placeholder(tf.int32, [batch_size, None])
    end_points = rnn_model(model='lstm',
                           input_data=input_data,
                           output_data=None,
                           vocab_size=len(word_to_int),
                           rnn_size=128,
                           num_layers=2,
                           batch_size=64,
                           learning_rate=0.0002)

    saver = tf.train.Saver(tf.global_variables())
    init_op = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
    with tf.Session() as sess:
        sess.run(init_op)

        checkpoint = tf.train.latest_checkpoint(conf.model_dir)
        saver.restore(sess, checkpoint)
        print("loading model from the checkpoint {0}".format(checkpoint))
        x = np.array([list(map(word_to_int.get, START_TOKEN))])
        [predict, last_state] = sess.run([end_points['prediction'],
                                          end_points['last_state']],
                                         feed_dict={input_data: x})
        if begin_word:
            word = begin_word
        else:
            word = to_word(predict, vocabularies)
        sentence = ''
        i = 0
        while word != END_TOKEN and word != START_TOKEN and word != UNK_TOKEN:
            sentence += word
            i += 1
            if i >= 24:
                break
            x = np.zeros((1, 1))
            try:
                x[0, 0] = word_to_int[word]
            except KeyError:
                print("please enter a chinese char again.")
                break
            [predict, last_state] = sess.run([end_points['prediction'], end_points['last_state']],
                                             feed_dict={input_data: x, end_points['initial_state']: last_state})
            word = to_word(predict, vocabularies)

        return sentence


def ppl(sentence_list):
    ppl_list = []
    # load data dict
    word_to_int = load_word_dict(conf.word_dict_path)
    # init params
    batch_size = 1
    input_data = tf.placeholder(tf.int32, [batch_size, None])
    output_targets = tf.placeholder(tf.int32, [batch_size, None])
    # init model
    end_points = rnn_model(model='lstm',
                           input_data=input_data,
                           output_data=output_targets,
                           vocab_size=len(word_to_int),
                           rnn_size=128,
                           num_layers=2,
                           batch_size=batch_size,
                           learning_rate=conf.learning_rate)

    saver = tf.train.Saver(tf.global_variables())
    init_op = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
    with tf.Session() as sess:
        # init op
        sess.run(init_op)
        checkpoint = tf.train.latest_checkpoint(conf.model_dir)
        saver.restore(sess, checkpoint)
        print("loading model from the checkpoint {0}".format(checkpoint))

        # infer each sentence
        for sentence in sentence_list:
            ppl = 0
            # data idx
            x = [word_to_int[c] if c in word_to_int else word_to_int[UNK_TOKEN] for c in sentence]
            x = [word_to_int[START_TOKEN]] + x + [word_to_int[END_TOKEN]]
            print('x:', x)
            # reshape
            y = np.array(x[1:]).reshape((-1, batch_size))
            x = np.array(x[:-1]).reshape((-1, batch_size))
            print(x.shape)
            print(y.shape)
            # get each word perplexity
            for i in range(x.shape[0]):
                perplexity = sess.run(end_points['perplexity'],
                                      feed_dict={input_data: x[i:i + 1, :],
                                                 output_targets: y[i:i + 1, :]})
                print('{0} -> {1}, perplexity: {2}'.format(x[i:i + 1, :], y[i:i + 1, :], perplexity))
                ppl += perplexity
            ppl = ppl / x.shape[0]
            print('perplexity:' + str(ppl))
            ppl_list.append(ppl)
    return ppl_list


def infer_generate():
    # begin_char = input('please input the first character:')
    begin_char = '我'
    print(generate(begin_char))


if __name__ == '__main__':
    sentences = ['化肥和农药不仅对人类有害',  # perplexity:4277.740985026727
                 '化肥和浓药不仅对人类有害',  # perplexity:5492552.78279785
                 '化肥和浓药不仅对人类有海',  # perplexity:5505405.811695649
                 '化肥和农药不仅对人类有害，而且对海洋危害很大']  # perplexity:21851.84118722833
    ppl(sentences)
