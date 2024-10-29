# Contains all functions that deal with stop word removal.

from document import Document
import re
import os
import json
DATA_PATH = 'data'
STOPWORD_FILE_PATH = os.path.join(DATA_PATH, 'stopwords.json')
def remove_symbols(text_string: str) -> str:
    """
    Removes all punctuation marks and similar symbols from a given string.
    Occurrences of "'s" are removed as well.
    :param text:
    :return:
    """

    punctuation_marks=['\'s','\.','\?','!',',',';','_','-','\(','\)','\[','\]','"',"'",'/','\n']
    for mark in punctuation_marks:
        if mark != '\n':
            text_string=re.sub(mark,'',text_string)
        else:
            text_string=re.sub(mark,' ',text_string)
    
    text_string=text_string.strip()

    return text_string
        


def is_stop_word(term: str, stop_word_list: list[str]) -> bool:
    """
    Checks if a given term is a stop word.
    :param stop_word_list: List of all considered stop words.
    :param term: The term to be checked.
    :return: True if the term is a stop word.
    """
    if term in stop_word_list:
        return True
    return False


def remove_stop_words_from_term_list(term_list: list[str]) -> list[str]:
    """
    Takes a list of terms and removes all terms that are stop words.
    :param term_list: List that contains the terms
    :return: List of terms without stop words
    """
    # Hint:  Implement the functions remove_symbols() and is_stop_word() first and use them here.
    stop_word_list=load_stop_word_list(STOPWORD_FILE_PATH)
    return [term for term in term_list if not is_stop_word(term, stop_word_list)]


def filter_collection(collection: list[Document]):
    """
    For each document in the given collection, this method takes the term list and filters out the stop words.
    Warning: The result is NOT saved in the documents term list, but in an extra field called filtered_terms.
    :param collection: Document collection to process
    """
    # Hint:  Implement remove_stop_words_from_term_list first and use it here.
    # TODO: Implement this function. (PR02)
    for i in range(len(collection)):
        collection[i].filtered_terms=remove_stop_words_from_term_list(collection[i].terms)



def load_stop_word_list(raw_file_path: str) -> list[str]:
    """
    Loads a text file that contains stop words and saves it as a list. The text file is expected to be formatted so that
    each stop word is in a new line, e. g. like englishST.txt
    :param raw_file_path: Path to the text file that contains the stop words
    :return: List of stop words
    """
    try:
        if raw_file_path.endswith('.json'):
            with open(raw_file_path, 'r') as file:
                return json.load(file)
        elif raw_file_path.endswith('.txt'):
            with open(raw_file_path, 'r') as file:
                stop_words = [line.strip() for line in file.readlines() if line.strip()]
                return stop_words
        else:
            return []

        
    except FileNotFoundError:
        return []


def create_stop_word_list_by_frequency(collection: list[Document]) -> list[str]:
    """
    Uses the method of J. C. Crouch (1990) to generate a stop word list by finding high and low frequency terms in the
    provided collection.
    :param collection: Collection to process
    :return: List of stop words
    """
    
    stop_words=[]
    high_frequency_threshold=0.6
    low_frequency_threshold=0.01

    words_frequency={}

    for doc in collection:
        for term in doc.terms:
            if term not in words_frequency.keys():
                words_frequency[term]=1
                continue
            else:
                words_frequency[term]+=1
                continue
    
    for term in words_frequency.keys():
        if words_frequency[term]<=low_frequency_threshold*len(collection) or words_frequency[term]>=high_frequency_threshold*len(collection):
            stop_words.append(term)

    return stop_words   
