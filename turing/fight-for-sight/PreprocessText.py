from nltk.stem import WordNetLemmatizer 
from nltk.corpus import stopwords

def lemmatize_abstracts(abstracts):
    '''Preprocess abstracts by: removing missing/very short abstracts, converting
    to lower case, removing punctuation and digits, removing stop words, and
    lemmatising with nltk WordNetLemmatizer.
    
    abstracts: pandas series.
    
    returns abstracts: pandas series of processed abstracts'''
    
    # remove missing/very short abstracts
    print('Removing missing abstracts')
    abstracts = abstracts.dropna()
    abstracts = abstracts[abstracts.str.split(r'[^a-zA-Z]+').str.len()>10]
    
    # convert to lower case and remove digits and punctuation
    print('Initial preprocessing: case, punctuation, whitespace')
    abstracts = abstracts.str.lower()
    abstracts = abstracts.str.replace(r'[^a-zA-Z]+',' ',regex=True)
    abstracts = abstracts.str.strip()
    abstracts= abstracts.str.split(' ')

    print('Lemmatizing')
    try:
        lemma = WordNetLemmatizer()
    except:
        import nltk
        nltk.download('wordnet')
        lemma = WordNetLemmatizer()

    try:
        stop_words = stopwords.words('english')
    except:
        import nltk
        nltk.download('stopwords')
        stop_words = stopwords.words('english')

    abstracts=abstracts.apply(lambda x : [lemma.lemmatize(word) for word in x if word not in stop_words])
    abstracts=abstracts.apply(lambda x : [word for word in x if len(word)>1])
    abstracts=abstracts.apply(lambda x : ' '.join(x))

    return abstracts