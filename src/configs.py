def get_config():
    conf = {
        'workdir': './data/java_corpus/',
        # data_params
        # training data
        'train_db': 'java_train',
        # test data
        'valid_db': 'java_valid',
        # use data (computing code vectors)
        'use_db': 'java_use',
        'use_codebase': 'use.rawcode.txt',
        # results data(code vectors)
        'use_codevecs': 'use.codevecs.normalized.h5',  # 'use.codevecs100.128.normalized.h5',  # 'use.codevecs.h5'

        # parameters
        'name_len': 6,
        'api_len': 30,
        'tokens_len': 50,
        'desc_len': 30,
        'n_words': 10000,  # len(vocabulary) + 1
        # vocabulary info
        'vocab_name': 'vocab.methname.pkl',
        'vocab_api': 'vocab.apiseq.pkl',
        'vocab_tokens': 'vocab.tokens.pkl',
        'vocab_desc': 'vocab.desc.pkl',

        'top_names': 10000,
        'top_apis': 10000,
        'top_tokens': 10000,
        'top_descs': 10000,

        # training_params
        'batch_size': 128,
        'chunk_size': 2000000,
        'nb_epoch': 1000,
        # 'validation_split': 0.2,
        # 'optimizer': 'adam',
        'lr': 0.001,
        'valid_every': 5,
        'n_eval': 100,
        # 'evaluate_all_threshold': {
        #     'mode': 'all',
        #     'top1': 0.4,
        # },
        'log_every': 100,
        'save_every': 5,
        'reload': 0,  # epoch that the model is reloaded from . If reload=0, then train from scratch

        'model_name': "java_cs_v2",

        # model_params
        'emb_size': 100,
        'n_hidden': 400,  # number of hidden dimension of code/desc representation
        # recurrent
        'lstm_dims': 200,  # * 2
        # 'init_embed_weights_methname': None,  # 'word2vec_100_methname.h5',
        # 'init_embed_weights_tokens': None,  # 'word2vec_100_tokens.h5',
        # 'init_embed_weights_desc': None,  # 'word2vec_100_desc.h5',
        'margin': 0.05,
        # 'sim_measure': 'cos',  # similarity measure: gesd, cosine, aesd

    }
    return conf
