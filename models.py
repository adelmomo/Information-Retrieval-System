# Contains all retrieval models.

from abc import ABC, abstractmethod

from document import Document
from cleanup import load_stop_word_list
from cleanup import remove_symbols
from cleanup import remove_stop_words_from_term_list
import extraction
import porter
import os
import math
import re
class RetrievalModel(ABC):
    @abstractmethod
    def document_to_representation(self, document: Document, stopword_filtering=False, stemming=False):
        """
        Converts a document into its model-specific representation.
        This is an abstract method and not meant to be edited. Implement it in the subclasses!
        :param document: Document object to be represented
        :param stopword_filtering: Controls, whether the document should first be freed of stopwords
        :param stemming: Controls, whether stemming is used on the document's terms
        :return: A representation of the document. Data type and content depend on the implemented model.
        """
        raise NotImplementedError()

    @abstractmethod
    def query_to_representation(self, query: str):
        """
        Determines the representation of a query according to the model's concept.
        :param query: Search query of the user
        :return: Query representation in whatever data type or format is required by the model.
        """
        raise NotImplementedError()

    @abstractmethod
    def match(self, document_representation, query_representation) -> float:
        """
        Matches the query and document presentation according to the model's concept.
        :param document_representation: Data that describes one document
        :param query_representation:  Data that describes a query
        :return: Numerical approximation of the similarity between the query and document representation. Higher is
        "more relevant", lower is "less relevant".
        """
        raise NotImplementedError()


class LinearBooleanModel(RetrievalModel):
    DATA_PATH = 'data'
    STOPWORD_FILE_PATH = os.path.join(DATA_PATH, 'stopwords.json')

    def __init__(self):
        self.stop_words=load_stop_word_list(self.STOPWORD_FILE_PATH)

    def __str__(self):
        return 'Boolean Model (Linear)'
    def document_to_representation(self, document: Document, stopword_filtering=False, stemming=False) -> list[str]:
        results=[]
        if stopword_filtering:
            results=remove_stop_words_from_term_list(document.terms)
            if stemming:
                results=[porter.stem_term(term) for term in results]
                return results
            return results
        if stemming:
            results=[porter.stem_term(term) for term in document.terms]
            return results
        return document.terms
        
        
    def query_to_representation(self, query: str) -> str:
        query=query.lower()
        return query
    
    def match(self, document_representation, query_representation) -> float:
        return query_representation in document_representation


class InvertedListBooleanModel(RetrievalModel):
    
    def __init__(self):
        self.stemmed_inverted_list={}
        self.non_stemmed_inverted_list={}
        DATA_PATH = 'data'
        COLLECTION_PATH = os.path.join(DATA_PATH, 'my_collection.json')
        collection=extraction.load_collection_from_json(COLLECTION_PATH)
        porter.stem_all_documents(collection)
        for doc in collection:
            for term in doc.stemmed_terms:
                if term not in self.stemmed_inverted_list.keys():
                    self.stemmed_inverted_list[term]=[doc.document_id]
                else:
                    self.stemmed_inverted_list[term].append(doc.document_id)
            
            for term in doc.terms:
                if term not in self.non_stemmed_inverted_list.keys():
                    self.non_stemmed_inverted_list[term]=[doc.document_id]
                else:
                    self.non_stemmed_inverted_list[term].append(doc.document_id)
        
        for term in self.stemmed_inverted_list.keys():
            self.stemmed_inverted_list[term]=set(sorted(self.stemmed_inverted_list[term]))

        for term in self.non_stemmed_inverted_list.keys():
            self.non_stemmed_inverted_list[term]=set(sorted(self.non_stemmed_inverted_list[term]))
    
    def query_to_representation(self, query: str) -> str:
        query=query.lower()
        return query
    def document_to_representation(self, document: Document, stopword_filtering=False, stemming=False) -> list[str]:
        pass
    def match(self, document_representation, query_representation) -> float:

        pass

    def __str__(self):
        return 'Boolean Model (Inverted List)'


class SignatureBasedBooleanModel(RetrievalModel):


    def __init__(self):
        self.F=64
        self.D=4
        self.m=3
        self.primes=self.generate_primes()
        self.non_stemmed_signature_files={}
        self.stemmed_signature_files={}
        self.stemmed_filtered_signature_files={}
        self.non_stemmed_filtered_signature_files={}
        DATA_PATH = 'data'
        COLLECTION_PATH = os.path.join(DATA_PATH, 'my_collection.json')
        self.collection=extraction.load_collection_from_json(COLLECTION_PATH)
        porter.stem_all_documents(self.collection)
        for i in range(len(self.collection)):
            
            self.stemmed_signature_files[self.collection[i].document_id]=[]
            self.non_stemmed_signature_files[self.collection[i].document_id]=[]
            self.stemmed_filtered_signature_files[self.collection[i].document_id]=[]
            self.non_stemmed_filtered_signature_files[self.collection[i].document_id]=[]

            #signatures for stemmed terms
            block_signature=0
            for j in range(len(self.collection[i].stemmed_terms)):
                term_signature=self.get_hash(self.collection[i].stemmed_terms[j])
                block_signature|=term_signature
                if (j+1)%self.D==0:
                    self.stemmed_signature_files[i].append(block_signature)
                    block_signature=0
            if len(self.collection[i].stemmed_terms)%self.D!=0:
                self.stemmed_signature_files[i].append(block_signature)

            #signatures for non stemmed terms
            block_signature=0
            for j in range(len(self.collection[i].terms)):
                term_signature=self.get_hash(self.collection[i].terms[j])
                block_signature|=term_signature
                if (j+1)%self.D==0:
                    self.non_stemmed_signature_files[i].append(block_signature)
                    block_signature=0
            if len(self.collection[i].terms)%self.D!=0:
                self.non_stemmed_signature_files[i].append(block_signature)

            #signatures for filtered non stemmed terms
            block_signature=0
            for j in range(len(self.collection[i].filtered_terms)):
                term_signature=self.get_hash(self.collection[i].filtered_terms[j])
                block_signature|=term_signature
                if (j+1)%self.D==0:
                    self.non_stemmed_filtered_signature_files[i].append(block_signature)
                    block_signature=0
            if len(self.collection[i].filtered_terms)%self.D!=0:
                self.non_stemmed_filtered_signature_files[i].append(block_signature)

            #signatures for filtered stemmed terms
            block_signature=0
            for j in range(len(self.collection[i].filtered_terms)):
                term_signature=self.get_hash(porter.stem_term(self.collection[i].filtered_terms[j]))
                block_signature|=term_signature
                if (j+1)%self.D==0:
                    self.stemmed_filtered_signature_files[i].append(block_signature)
                    block_signature=0
            if len(self.collection[i].filtered_terms)%self.D!=0:
                self.stemmed_filtered_signature_files[i].append(block_signature)


    def match(self, document_representation, query_representation) -> float:
        pattern_signature=self.get_hash(query_representation)
        for block_signature in document_representation:
            if block_signature&pattern_signature:
                return 1.0
        return 0.0
    
    def query_to_representation(self, query: str) -> str:
        query=query.lower()
        return query
    
    def document_to_representation(self, document: Document, stopword_filtering=False, stemming=False) -> list[str]:
        pass

    def get_hash(self,word):
        
        result=0
        for p in self.primes:
            current_hash=0
            for i in range(len(word)):
                current_hash=(current_hash+(ord(word[i])-ord('a')+1))*p
                current_hash=current_hash % self.F
            result=result|(2**current_hash)
            result=result % (2**self.F)

            if self.count_set_bits(result)>=self.m:
                break
        for bit in range(self.F):
            if self.count_set_bits(result)>=self.m:
                break
        
           
            if result&(1<<bit)==0:
                result|=(1<<bit)    
        
        return result
    

    def count_set_bits(self,hash_value):
        counter=0
        while hash_value>0:
            if hash_value%2!=0:
                counter+=1
            
            hash_value=hash_value//2
        return counter
    
    def generate_primes(self, max_prime_value=1000):
        # Initialize a boolean list for marking non-primes
        is_prime = [True] * (max_prime_value + 1)
        primes = []

        for i in range(2, max_prime_value + 1):
            if is_prime[i]:
                primes.append(i)
                # Mark all multiples of `i` as non-prime
                for multiple in range(i * i, max_prime_value + 1, i):
                    is_prime[multiple] = False

        return primes
            
    def __str__(self):
        return 'Boolean Model (Signatures)'


class VectorSpaceModel(RetrievalModel):
   
    def __init__(self):
        self.stemmed_inverted_list={}
        self.non_stemmed_inverted_list={}
        DATA_PATH = 'data'
        COLLECTION_PATH = os.path.join(DATA_PATH, 'my_collection.json')
        collection=extraction.load_collection_from_json(COLLECTION_PATH)
        self.N=len(collection)
        self.stemmed_n={}
        self.stemmed_norms={}
        self.non_stemmed_norms={}
        self.non_stemmed_n={}
        porter.stem_all_documents(collection)

        for doc in collection:
            for t in list(set(doc.stemmed_terms)):
                if not t in self.stemmed_n.keys():
                    self.stemmed_n[t]=1
                else:
                    self.stemmed_n[t]+=1

            for t in list(set(doc.terms)):
                if not t in self.non_stemmed_n.keys():
                    self.non_stemmed_n[t]=1
                else:
                    self.non_stemmed_n[t]+=1
        for doc in collection:
            self.stemmed_norms[doc.document_id]=self.get_document_norm(doc.document_id,collection,True)
            self.non_stemmed_norms[doc.document_id]=self.get_document_norm(doc.document_id,collection,False)

        for doc in collection:
            stemmed_terms=list(set(doc.stemmed_terms))
            non_stemmed_terms=list(set(doc.terms))

            for term in stemmed_terms:
                if term not in self.stemmed_inverted_list.keys():
                    self.stemmed_inverted_list[term]=[(doc.document_id,self.get_term_weight(term,doc.document_id,collection,True))]
                else:
                    self.stemmed_inverted_list[term].append((doc.document_id,self.get_term_weight(term,doc.document_id,collection,True)))
            
            for term in non_stemmed_terms:
                if term not in self.non_stemmed_inverted_list.keys():
                    self.non_stemmed_inverted_list[term]=[(doc.document_id,self.get_term_weight(term,doc.document_id,collection,False))]
                else:
                    self.non_stemmed_inverted_list[term].append((doc.document_id,self.get_term_weight(term,doc.document_id,collection,False)))
        
        for term in self.stemmed_inverted_list.keys():
            self.stemmed_inverted_list[term]=sorted(self.stemmed_inverted_list[term],key=lambda pair:pair[1],reverse=True)

        for term in self.non_stemmed_inverted_list.keys():
            self.non_stemmed_inverted_list[term]=sorted(self.non_stemmed_inverted_list[term],key=lambda pair:pair[1],reverse=True)
    def get_term_weight(self,term,document,collection,stemming=False):
        relative_frequency=0
        absolute_frequency=0
        N=len(collection)
        if stemming:
            for t in collection[document].stemmed_terms:
                if term==t:
                    relative_frequency+=1
        else:
            for t in collection[document].terms:
                if term==t:
                    relative_frequency+=1
        
        if stemming:
            absolute_frequency=self.stemmed_n[term]
        else:
            absolute_frequency=self.non_stemmed_n[term]
        
        if stemming:
            document_norm=self.stemmed_norms[document]
        else:
            document_norm=self.non_stemmed_norms[document]
        term_weight=relative_frequency*math.log(N/absolute_frequency)
        return term_weight/document_norm

    def get_query_term_weight(self,query_terms,term,stemming=False):
        relative_frequency=0
        
        for t in query_terms:
            if term==t:
                relative_frequency+=1
        max_relative_frequency=1
        relative_frequencies={}
        for i in range(len(query_terms)):
            if query_terms[i] not in relative_frequencies.keys():
                relative_frequencies[query_terms[i]]=1
            else:
                relative_frequencies[query_terms[i]]+=1
            max_relative_frequency=max(max_relative_frequency,relative_frequencies[query_terms[i]])
        if stemming:
            if term not in self.stemmed_inverted_list.keys():
                return 0
            absolute_frequency=len(self.stemmed_inverted_list[term])
        else:
            if term not in self.non_stemmed_inverted_list.keys():
                return 0
            absolute_frequency=len(self.non_stemmed_inverted_list[term])
        if relative_frequency>0:
            term_weight=(0.5+(0.5*relative_frequency/max_relative_frequency))*math.log(self.N/absolute_frequency)
        else:
            term_weight=0
    
        return term_weight
                
    def get_document_norm(self,document,collection,stemming=False):
        if stemming:
            terms=list(set(collection[document].stemmed_terms))
        else:
            terms=list(set(collection[document].terms))    
        document_norm=0
        N=len(collection)
        for t in terms:
            relative_frequency=0
            absolute_frequency=0
            if stemming:
                for i in range(len(collection[document].stemmed_terms)):
                    if t==collection[document].stemmed_terms[i]:
                        relative_frequency+=1
            else:
                for i in range(len(collection[document].terms)):
                    if t==collection[document].terms[i]:
                        relative_frequency+=1
            if stemming:
                absolute_frequency=self.stemmed_n[t]
            else:
                absolute_frequency=self.non_stemmed_n[t]
            document_norm+=(relative_frequency*math.log(N/absolute_frequency))**2
        document_norm=math.sqrt(document_norm)
        return document_norm  
    
    def query_to_representation(self, query: str) -> str:
        query=query.lower()
        query=query.strip()
        query=re.sub(' +',' ',query)
        return query
    
    def document_to_representation(self, document: Document, stopword_filtering=False, stemming=False) -> list[str]:
        pass
    
    def match(self, document_representation, query_representation) -> float:
        pass


    def __str__(self):
        return 'Vector Space Model'


class FuzzySetModel(RetrievalModel):

    def __init__(self):
        raise NotImplementedError()  # TODO: Remove this line and implement the function.

    def __str__(self):
        return 'Fuzzy Set Model'
