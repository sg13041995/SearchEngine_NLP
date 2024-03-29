# ==================================
# MODULES
# ==================================

# general
import numpy as np
import re
import json

# data/model import export
import pickle
import joblib

# nltk
from nltk.tokenize import word_tokenize

# gensim
from gensim.models import TfidfModel
from gensim.corpora import Dictionary
from gensim.models import OkapiBM25Model
from gensim.similarities import SparseMatrixSimilarity

# database MariaDB
from configparser import ConfigParser
from mysql.connector import MySQLConnection, Error
from datetime import datetime

# ==================================
# FUNCTIONS
# ==================================

# read pikle files
def read_pkl(path, mode="rb"):
    with open(path, mode) as file:
        data = pickle.load(file)
        return data


# retrain the BM25 gensim model with new data
def retrain_gensim_bm25(tokenized_documents):
    dictionary = Dictionary(tokenized_documents)
    bm25_model = OkapiBM25Model(dictionary=dictionary)
    bm25_corpus = bm25_model[list(
        map(dictionary.doc2bow, tokenized_documents))]
    bm25_index = SparseMatrixSimilarity(bm25_corpus,
                                        num_docs=len(tokenized_documents),
                                        num_terms=len(dictionary),
                                        normalize_queries=False,
                                        normalize_documents=False)
    tfidf_model = TfidfModel(dictionary=dictionary, smartirs='bnn')

    return dictionary, bm25_index, tfidf_model


# getting indices of top n matches
def bm25_top_hits(query: str,
                  tfidf_model: TfidfModel,
                  bm25_index: SparseMatrixSimilarity,
                  dictionary: Dictionary,
                  n=50):
    
    # initial cleaning of the query string
    # lower case, remove unwanted charactrers and space
    processed = re.sub("\s+", " ", re.sub("[^a-zA-Z0-9 ]", "", query.lower()))
    # tokenizing the query string
    tokenized_query = word_tokenize(processed)

    # Enforce binary weighting of queries
    tfidf_query = tfidf_model[dictionary.doc2bow(tokenized_query)]
    similarities = bm25_index[tfidf_query]

    if (similarities.max() > 0):
        # getting document indices based on BM25 top scores in descending order
        top_n_index = np.argsort(similarities, axis=0)[::-1]
        
        top_n_index = top_n_index[:n]
        top_n_scores = similarities[top_n_index]

        filtered_index = np.where(top_n_scores != 0)
        final_index = top_n_index[filtered_index]

        # increasing all indices values by 1 and then return that list
        return final_index + 1
    else:
        return None


# reading and parsing the database credential file
def read(filename='config.ini', section='mysql'):
    parser = ConfigParser()
    parser.read(filename)

    db = {}

    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db[item[0]] = item[1]
    else:
        raise Exception(f'{section} not found in file {filename}')
    return db


# connecting with the database
def connect(creds):
    con = None
    try:
        print('Connecting to MySQL database...')
        con = MySQLConnection(**creds)

        if con.is_connected():
            print('Connection established')
            cus = con.cursor(buffered=True)
        else:
            print('Connection failed')

    except Error as e:
        print(e)
    finally:
        return con, cus


# converting a list into string
def list_to_str(data):
    return str(data).lstrip("[").rstrip("]")


# get all the columns from the database with provided indices
def book_alldetails_byindex(
        indices,
        cs,
        proc_name="sp_get_books_by_index",
        proc_args_initial=[0]
):
    indices_as_str = list_to_str(list(indices))

    procs_args_complete = []
    procs_args_complete.extend(proc_args_initial)
    procs_args_complete.extend([indices_as_str])

    cs.callproc(proc_name, procs_args_complete)

    books = [r.fetchall() for r in cs.stored_results()]

    return books


# get the titles only from the database with provided indices
def book_onlytitles_byindex(
        indices,
        cs,
        proc_name="sp_get_titles_by_index",
        proc_args_initial=[0]
):
    indices_as_str = list_to_str(list(indices))

    procs_args_complete = []
    procs_args_complete.extend(proc_args_initial)
    procs_args_complete.extend([indices_as_str])

    cs.callproc(proc_name, procs_args_complete)
    titles = [r.fetchall() for r in cs.stored_results()]

    return titles



# get specific details for search engine from the database with provided indices
def book_searchdetails_byindex(
        indices,
        cs,
        proc_name="sp_get_books_by_index_search",
        proc_args_initial=[0]
):
    indices_as_str = list_to_str(list(indices))

    procs_args_complete = []
    procs_args_complete.extend(proc_args_initial)
    procs_args_complete.extend([indices_as_str])

    cs.callproc(proc_name, procs_args_complete)
    titles = [r.fetchall() for r in cs.stored_results()]

    return titles



# book_alldetails_byindex to json
def book_alldetails_tojson(data=None):
    if (data is not None):
        def mapping_function(x): return {
            "book_id": x[0],
            "gr_book_id": x[1],
            "title_without_series": x[2],
            "mod_title": x[3],
            "title": x[4],
            "mod_title_without_series": x[5],
            "description": x[6],
            "ratings_count": x[7],
            "average_rating": x[8],
            "num_pages": x[9],
            "publication_day": x[10],
            "publication_month": x[11],
            "publication_year": x[12],
            "isbn": x[13],
            "isbn13": x[14],
            "publisher": x[15],
            "country_code": x[16],
            "language_code": x[17],
            "url": x[18],
            "image_url": x[19],
            "link": x[20]
        }

        # Use map to apply the mapping function to each tuple
        list_of_dicts = list(map(mapping_function, data))

        json_data = json.dumps(list_of_dicts, indent=4)

        return json_data
    else:
        return json.dumps([])


# book_onlytitles_byindex to json
def book_onlytitles_tojson(data=None):
    if (data is not None):
        def mapping_function(x): return {
            "id": x[0],
            "book_title_mod": x[1][0],
        }

        # Use map to apply the mapping function to each tuple
        list_of_dicts = list(map(mapping_function, enumerate(data)))

        json_data = json.dumps(list_of_dicts, indent=4)

        return json_data
    else:
        return json.dumps([])



# book_alldetails_byindex to json
def book_searchdetails_tojson(data=None):
    if (data is not None):
        def mapping_function(x): return {
            "title": x[0],
            "description": x[1],
            "image": x[4],
            "price": str(x[3]),
        }

        # Use map to apply the mapping function to each tuple
        list_of_dicts = list(map(mapping_function, data))

        json_data = json.dumps(list_of_dicts, indent=4)

        return json_data
    else:
        return json.dumps([])