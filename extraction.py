import json

from document import Document
import re
import os
from cleanup import remove_symbols
def extract_collection(source_file_path: str) -> list[Document]:
    """
    Loads a text file (aesopa10.txt) and extracts each of the listed fables/stories from the file.
    :param source_file_name: File name of the file that contains the fables
    :return: List of Document objects
    """
    catalog = []  # This dictionary will store the document raw_data.

    with open(os.path.join(source_file_path), "r") as f:
        text = f.read()
    starting_point_of_stories=re.search(r"\n{3}Aesop's Fables",text)
    text_of_interest=text[starting_point_of_stories.end()+1:]
    stories=re.split(r'\n{3}', text_of_interest)[1:]

    document_id=0
    for i in range(len(stories)):
        if i%2==0:
            document=Document()
            document.title=stories[i].strip()
            document.document_id=document_id
            document_id+=1
        else:
            document.raw_text=remove_symbols(stories[i])
            document.raw_text=document.raw_text.lower()
            document.terms=document.raw_text.split(' ')

            catalog.append(document)




    return catalog


def save_collection_as_json(collection: list[Document], file_path: str) -> None:
    """
    Saves the collection to a JSON file.
    :param collection: The collection to store (= a list of Document objects)
    :param file_path: Path of the JSON file
    """

    serializable_collection = []
    for document in collection:
        serializable_collection += [{
            'document_id': document.document_id,
            'title': document.title,
            'raw_text': document.raw_text,
            'terms': document.terms,
            'filtered_terms': document.filtered_terms,
            'stemmed_terms': document.stemmed_terms
        }]

    with open(file_path, "w") as json_file:
        json.dump(serializable_collection, json_file)


def load_collection_from_json(file_path: str) -> list[Document]:
    """
    Loads the collection from a JSON file.
    :param file_path: Path of the JSON file
    :return: list of Document objects
    """
    try:
        with open(file_path, "r") as json_file:
            json_collection = json.load(json_file)

        collection = []
        for doc_dict in json_collection:
            document = Document()
            document.document_id = doc_dict.get('document_id')
            document.title = doc_dict.get('title')
            document.raw_text = doc_dict.get('raw_text')
            document.terms = doc_dict.get('terms')
            document.filtered_terms = doc_dict.get('filtered_terms')
            document.stemmed_terms = doc_dict.get('stemmed_terms')
            collection += [document]

        return collection
    except FileNotFoundError:
        print('No collection was found. Creating empty one.')
        return []
