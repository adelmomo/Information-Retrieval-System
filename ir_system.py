import json
import os

import cleanup
import extraction
import models
import porter
from document import Document
from pyparsing import Word, alphas, infixNotation, opAssoc
import pyparsing
import time
identifier = Word(alphas)
and_op = '&'
or_op = '|'
not_op = '-'

expr = infixNotation(
    identifier,
    [
        (not_op, 1, opAssoc.RIGHT),
        (and_op, 2, opAssoc.LEFT),
        (or_op, 2, opAssoc.LEFT),
    ]
)
# Important paths:
RAW_DATA_PATH = 'raw_data'
DATA_PATH = 'data'
COLLECTION_PATH = os.path.join(DATA_PATH, 'my_collection.json')
STOPWORD_FILE_PATH = os.path.join(DATA_PATH, 'stopwords.json')

# Menu choices:
(CHOICE_LIST, CHOICE_SEARCH, CHOICE_EXTRACT, CHOICE_UPDATE_STOP_WORDS, CHOICE_SET_MODEL, CHOICE_SHOW_DOCUMENT,
 CHOICE_EXIT) = 1, 2, 3, 4, 5, 6, 9
MODEL_BOOL_LIN, MODEL_BOOL_INV, MODEL_BOOL_SIG, MODEL_FUZZY, MODEL_VECTOR = 1, 2, 3, 4, 5
SW_METHOD_LIST, SW_METHOD_CROUCH = 1, 2


class InformationRetrievalSystem(object):
    def __init__(self):
        if not os.path.isdir(DATA_PATH):
            os.makedirs(DATA_PATH)

        # Collection of documents, initially empty.
        try:
            self.collection = extraction.load_collection_from_json(COLLECTION_PATH)
        except FileNotFoundError:
            print('No previous collection was found. Creating empty one.')
            self.collection = []

        # Stopword list, initially empty.
        try:
            with open(STOPWORD_FILE_PATH, 'r') as f:
                self.stop_word_list = json.load(f)
        except FileNotFoundError:
            print('No stopword list was found.')
            self.stop_word_list = []

        self.model = None  # Saves the current IR model in use.
        self.output_k = 10  # Controls how many results should be shown for a query.


    def main_menu(self):
        """
        Provides the main loop of the CLI menu that the user interacts with.
        """
        while True:
            print(f'Current retrieval model: {self.model}')
            print(f'Current collection: {len(self.collection)} documents')
            print()
            print('Please choose an option:')
            print(f'{CHOICE_LIST} - List documents')
            print(f'{CHOICE_SEARCH} - Search for term')
            print(f'{CHOICE_EXTRACT} - Build collection')
            print(f'{CHOICE_UPDATE_STOP_WORDS} - Rebuild stopword list')
            print(f'{CHOICE_SET_MODEL} - Set model')
            print(f'{CHOICE_SHOW_DOCUMENT} - Show a specific document')
            print(f'{CHOICE_EXIT} - Exit')
            action_choice = int(input('Enter choice: '))

            if action_choice == CHOICE_LIST:
                # List documents in CLI.
                if self.collection:
                    for document in self.collection:
                        print(document)
                else:
                    print('No documents.')
                print()

            elif action_choice == CHOICE_SEARCH:
                # Read a query string from the CLI and search for it.

                # Determine desired search parameters:
                SEARCH_NORMAL, SEARCH_SW, SEARCH_STEM, SEARCH_SW_STEM = 1, 2, 3, 4
                print('Search options:')
                print(f'{SEARCH_NORMAL} - Standard search (default)')
                print(f'{SEARCH_SW} - Search documents with removed stopwords')
                print(f'{SEARCH_STEM} - Search documents with stemmed terms')
                print(f'{SEARCH_SW_STEM} - Search documents with removed stopwords AND stemmed terms')
                search_mode = int(input('Enter choice: '))
                stop_word_filtering = (search_mode == SEARCH_SW) or (search_mode == SEARCH_SW_STEM)
                stemming = (search_mode == SEARCH_STEM) or (search_mode == SEARCH_SW_STEM)

                # Actual query processing begins here:
                query = input('Query: ')
                if stemming:
                    query = porter.stem_query_terms(query)
                start_time=time.time()
                if isinstance(self.model, models.InvertedListBooleanModel):
                    results = self.inverted_list_search(query, stemming, stop_word_filtering)
                elif isinstance(self.model, models.VectorSpaceModel):
                    results = self.buckley_lewit_search(query, stemming, stop_word_filtering)
                elif isinstance(self.model, models.SignatureBasedBooleanModel):
                    results = self.signature_search(query, stemming, stop_word_filtering)
                else:
                    results = self.basic_query_search(query, stemming, stop_word_filtering)

                ranked_results=sorted(results, key=lambda x: x[0], reverse=True)
                
                print(f'Top {self.output_k} Relevant Documents:')
                # Output of results:
                for (score, document) in ranked_results[:self.output_k]:
                    print(f'{score}: {document}')

                # Output of quality metrics:
                print()
                print(f'precision: {self.calculate_precision(query,results)}')
                print(f'recall: {self.calculate_recall(query,results)}')

                # Measure and print query processing time in ms
                
                end_time = time.time()
                processing_time_ms = (end_time - start_time) * 1000
                print(f'Query processing time: {processing_time_ms:.2f} ms')

            elif action_choice == CHOICE_EXTRACT:
                # Extract document collection from text file.

                raw_collection_file = os.path.join(RAW_DATA_PATH, 'aesopa10.txt')
                self.collection = extraction.extract_collection(raw_collection_file)
                assert isinstance(self.collection, list)
                assert all(isinstance(d, Document) for d in self.collection)

                if input('Should stopwords be filtered? [y/N]: ') == 'y':
                    cleanup.filter_collection(self.collection)

                if input('Should stemming be performed? [y/N]: ') == 'y':
                    porter.stem_all_documents(self.collection)

                extraction.save_collection_as_json(self.collection, COLLECTION_PATH)
                print('Done.\n')

            elif action_choice == CHOICE_UPDATE_STOP_WORDS:
                # Rebuild the stop word list, using one out of two methods.

                print('Available options:')
                print(f'{SW_METHOD_LIST} - Load stopword list from file')
                print(f"{SW_METHOD_CROUCH} - Generate stopword list using Crouch's method")

                method_choice = int(input('Enter choice: '))
                if method_choice in (SW_METHOD_LIST, SW_METHOD_CROUCH):
                    # Load stop words using the desired method:
                    if method_choice == SW_METHOD_LIST:
                        self.stop_word_list = cleanup.load_stop_word_list(os.path.join(RAW_DATA_PATH, 'englishST.txt'))
                        print('Done.\n')
                    elif method_choice == SW_METHOD_CROUCH:
                        self.stop_word_list = cleanup.create_stop_word_list_by_frequency(self.collection)
                        print('Done.\n')

                    # Save new stopword list into file:
                    with open(STOPWORD_FILE_PATH, 'w') as f:
                        json.dump(self.stop_word_list, f)
                else:
                    print('Invalid choice.')

            elif action_choice == CHOICE_SET_MODEL:
                # Choose and set the retrieval model to use for searches.

                print()
                print('Available models:')
                print(f'{MODEL_BOOL_LIN} - Boolean model with linear search')
                print(f'{MODEL_BOOL_INV} - Boolean model with inverted lists')
                print(f'{MODEL_BOOL_SIG} - Boolean model with signature-based search')
                print(f'{MODEL_FUZZY} - Fuzzy set model')
                print(f'{MODEL_VECTOR} - Vector space model')
                model_choice = int(input('Enter choice: '))
                if model_choice == MODEL_BOOL_LIN:
                    self.model = models.LinearBooleanModel()
                elif model_choice == MODEL_BOOL_INV:
                    self.model = models.InvertedListBooleanModel()
                elif model_choice == MODEL_BOOL_SIG:
                    self.model = models.SignatureBasedBooleanModel()
                elif model_choice == MODEL_FUZZY:
                    self.model = models.FuzzySetModel()
                elif model_choice == MODEL_VECTOR:
                    self.model = models.VectorSpaceModel()
                else:
                    print('Invalid choice.')

            elif action_choice == CHOICE_SHOW_DOCUMENT:
                target_id = int(input('ID of the desired document:'))
                found = False
                for document in self.collection:
                    if document.document_id == target_id:
                        print(document.title)
                        print('-' * len(document.title))
                        print(document.raw_text)
                        found = True

                if not found:
                    print(f'Document #{target_id} not found!')

            elif action_choice == CHOICE_EXIT:
                break
            else:
                print('Invalid choice.')

            print()
            input('Press ENTER to continue...')
            print()

    def basic_query_search(self, query: str, stemming: bool, stop_word_filtering: bool) -> list:
        """
        Searches the collection for a query string. This method is "basic" in that it does not use any special algorithm
        to accelerate the search. It simply calculates all representations and matches them, returning a sorted list of
        the k most relevant documents and their scores.
        :param query: Query string
        :param stemming: Controls, whether stemming is used
        :param stop_word_filtering: Controls, whether stop-words are ignored in the search
        :return: List of tuples, where the first element is the relevance score and the second the corresponding
        document
        """
        def compute_expression_from_collection(expression)->set:

            result_set=set()
            last_operator=None
            is_negation=False
            for element in expression:
                if isinstance(element,pyparsing.results.ParseResults):
                    current_group_set=compute_expression_from_collection(element)
                    if is_negation:
                        union_set=set([d.document_id for d in self.collection])
                        
                        current_group_set=union_set.difference(current_group_set)
                        
                        is_negation=False
                    
                    if len(result_set)>0:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_group_set)
                            
                        elif last_operator=='|':
                            result_set=result_set.union(current_group_set)
                    else:
                        result_set=current_group_set
                    continue
                if element not in ['&','|']:
                    if element=='-':
                        is_negation=True
                        continue
                    if cleanup.is_stop_word(element,self.stop_word_list) and stop_word_filtering:
                        continue
                    
                    current_term=element
                    
                    current_term=cleanup.remove_symbols(current_term)
                    if stemming:
                        current_term=porter.stem_term(current_term)

                    current_term_set=set(get_terms_documents(current_term))
                    
                    
        
                    if is_negation:

                        union_set=set([d.document_id for d in self.collection])
                        
                        current_term_set=union_set.difference(current_term_set)
                        
                        is_negation=False
                    
                    if last_operator is None and len(result_set)==0:
                        result_set=current_term_set
                    else:
                        if last_operator=='&':
                          
                            result_set=result_set.intersection(current_term_set)
                            
                        elif last_operator=='|':
                            result_set=result_set.union(current_term_set)
                       
                else:
                    last_operator=element
        
            
            return result_set
        def get_terms_documents(term)->list:
            documents=[]
            for i in range(len(document_representations)):
                if self.model.match(document_representations[i],term)==1.0:
                    documents.append(self.collection[i].document_id)
            return documents
        
        query_representation = self.model.query_to_representation(query)
        queries=[query_representation]
        document_representations = [self.model.document_to_representation(d, stop_word_filtering, stemming)
                                    for d in self.collection]
        
        for qr in queries:
            #try:
                parsed_query = expr.parseString(qr)
                retrieved_documents=list(compute_expression_from_collection(parsed_query))
                
                results=[]
                for d in self.collection:
                    if d.document_id in retrieved_documents:
                        results.append((1.0,d))
                results=sorted(results, key=lambda x: x[0], reverse=True)
                return results
            #except:
            #     results=[]
            #     for d in self.collection:
            #             results.append((0.0,d.document_id))
            #     results=sorted(results, key=lambda x: x[0], reverse=True)
            #     return results

    def inverted_list_search(self, query: str, stemming: bool, stop_word_filtering: bool) -> list:
        """
        Fast Boolean query search for inverted lists.
        :param query: Query string
        :param stemming: Controls, whether stemming is used
        :param stop_word_filtering: Controls, whether stop-words are ignored in the search
        :return: List of tuples, where the first element is the relevance score and the second the corresponding
        document
        """
        def compute_expression_from_collection(expression)->set:
            result_set=set()
            last_operator=None
            is_negation=False
            for element in expression:
                if isinstance(element,pyparsing.results.ParseResults):
                    current_group_set=compute_expression_from_collection(element)
                    if is_negation:
                        union_set=set([d.document_id for d in self.collection])
                        
                        current_group_set=union_set.difference(current_group_set)
                        
                        is_negation=False
                    
                    if len(result_set)>0:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_group_set)
                            
                        elif last_operator=='|':
                            result_set=result_set.union(current_group_set)
                    else:
                        result_set=current_group_set
                    continue
                if element not in ['&','|']:
                    if element=='-':
                        is_negation=True
                        continue

                    if cleanup.is_stop_word(element,self.stop_word_list) and stop_word_filtering:
                        continue
                    
                    current_term=element
                    
                    current_term=cleanup.remove_symbols(current_term)
                    if stemming:
                        current_term=porter.stem_term(current_term)
                        current_term_set=set(self.model.stemmed_inverted_list[current_term])
                    else:
                        current_term_set=set(self.model.non_stemmed_inverted_list[current_term])
                    
        
                    if is_negation:
                        union_set=set([d.document_id for d in self.collection])
                        current_term_set=union_set.difference(current_term_set)
                        is_negation=False
                    
                    if last_operator is None and len(result_set)==0:
                        result_set=current_term_set
                    else:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_term_set)
                        elif last_operator=='|':
                            result_set=result_set.union(current_term_set)
                       
                else:
                    last_operator=element
        
            return result_set

                        
                    
        
        query_representation = self.model.query_to_representation(query)
        queries=[query_representation]
        for qr in queries:
            try:
                parsed_query = expr.parseString(qr)
                retrieved_documents=list(compute_expression_from_collection(parsed_query))
                
                results=[]
                for d in self.collection:
                    if d.document_id in retrieved_documents:
                        results.append((1.0,d))
                results=sorted(results, key=lambda x: x[0], reverse=True)
                return results
            except:
                results=[]
                return results

            


        


    def buckley_lewit_search(self, query: str, stemming: bool, stop_word_filtering: bool) -> list:
        """
        Fast query search for the Vector Space Model using the algorithm by Buckley & Lewit.
        :param query: Query string
        :param stemming: Controls, whether stemming is used
        :param stop_word_filtering: Controls, whether stop-words are ignored in the search
        :return: List of tuples, where the first element is the relevance score and the second the corresponding
        document
        """
        
        query=self.model.query_to_representation(query)
        raw_terms=query.split(' ')
        query_terms=[]
        query_vector=[]
        for i in range(len(raw_terms)):
            if cleanup.is_stop_word(raw_terms[i],self.stop_word_list) and stop_word_filtering:
                continue
                    
            current_term=raw_terms[i]
                    
            current_term=cleanup.remove_symbols(current_term)
            if stemming:
                current_term=porter.stem_term(current_term)
            query_terms.append(current_term)
        
        for t in list(set(query_terms)):
            query_vector.append((t,self.model.get_query_term_weight(query_terms,t,stemming)))
        query_vector=sorted(query_vector,key=lambda pair:pair[1],reverse=True)

        gamma=9
        auxiliary_data_structure={}
        top_docs=[]
        if stemming:
            inverted_list=self.model.stemmed_inverted_list
        else:
            inverted_list=self.model.non_stemmed_inverted_list
        for i,query_term in enumerate(query_vector):
            if query_term[1]>0:
            
                for document_weight_pair in inverted_list[query_term[0]]:
                    pair=document_weight_pair
                    if pair[0] not in auxiliary_data_structure.keys():
                        auxiliary_data_structure[pair[0]]=pair[1]*query_term[1]
                    else:
                        auxiliary_data_structure[pair[0]]+=pair[1]*query_term[1]
                
                    current_relevant_docs=[(doc,auxiliary_data_structure[doc]) for doc in list(auxiliary_data_structure.keys())]
                    current_relevant_docs=sorted(current_relevant_docs,key=lambda x:x[1],reverse=True)
                    top_docs=current_relevant_docs
                
                remaining_weights=0
                for j in range(i+1,len(query_vector)):
                    remaining_weights+=query_vector[j][1]
                
                if len(top_docs)>gamma:
                    if top_docs[gamma-1][1]>top_docs[gamma][1]+remaining_weights:
                        break
        top_docs=top_docs[:gamma+1] 
        
        results=[]
        for result in top_docs:
            results.append((result[1],self.collection[result[0]]))
        return results


                    
                

    def signature_search(self, query: str, stemming: bool, stop_word_filtering: bool) -> list:
        """
        Fast Boolean query search using signatures for quicker processing.
        :param query: Query string
        :param stemming: Controls, whether stemming is used
        :param stop_word_filtering: Controls, whether stop-words are ignored in the search
        :return: List of tuples, where the first element is the relevance score and the second the corresponding
        document
        """
        def compute_expression_from_collection(expression)->set:
                    result_set=set()
                    last_operator=None
                    is_negation=False
                    for element in expression:
                        if isinstance(element,pyparsing.results.ParseResults):
                            current_group_set=compute_expression_from_collection(element)
                            if is_negation:
                                union_set=set([d.document_id for d in self.collection])
                                
                                current_group_set=union_set.difference(current_group_set)
                                
                                is_negation=False
                            
                            if len(result_set)>0:
                                if last_operator=='&':
                                    result_set=result_set.intersection(current_group_set)
                                    
                                elif last_operator=='|':
                                    result_set=result_set.union(current_group_set)
                            else:
                                result_set=current_group_set
                            continue
                            
                        if element not in ['&','|']:
                            if element=='-':
                                is_negation=True
                                continue

                            if cleanup.is_stop_word(element,self.stop_word_list) and stop_word_filtering:
                                continue
                            
                            current_term=element
                            
                            current_term=cleanup.remove_symbols(current_term)
                            if stemming:
                                current_term=porter.stem_term(current_term)
                            
                            current_term_set=set(get_terms_documents(current_term,stemming,stop_word_filtering))
                            
                
                            if is_negation:
                                union_set=set([d.document_id for d in self.collection])
                                
                                current_term_set=union_set.difference(current_term_set)
                                is_negation=False
                            
                            if last_operator is None and len(result_set)==0:
                                result_set=current_term_set
                            else:
                                if last_operator=='&':
                                    result_set=result_set.intersection(current_term_set)
                                elif last_operator=='|':
                                    result_set=result_set.union(current_term_set)
                            
                        else:
                            last_operator=element
                
                    return result_set

        def get_terms_documents(term,stemming,stop_word_filtering)->list:
            candidates=[]
            if stemming and stop_word_filtering:
                for document in list(self.model.stemmed_filtered_signature_files.keys()):
                    if self.model.match(self.model.stemmed_filtered_signature_files[document],term)==1.0:
                        candidates.append(document)
            elif stemming:
                for document in list(self.model.stemmed_signature_files.keys()):
                    if self.model.match(self.model.stemmed_signature_files[document],term)==1.0:
                        candidates.append(document)
            elif stop_word_filtering:
                for document in list(self.model.non_stemmed_filtered_signature_files.keys()):
                    if self.model.match(self.model.non_stemmed_filtered_signature_files[document],term)==1.0:
                        candidates.append(document)
            else:
                for document in list(self.model.non_stemmed_signature_files.keys()):
                    if self.model.match(self.model.non_stemmed_signature_files[document],term)==1.0:
                        candidates.append(document)
            documents=[]
            for candidate in candidates:
                if stemming:
                    if term in self.model.collection[candidate].stemmed_terms:
                        documents.append(candidate)
                else:
                    if term in self.model.collection[candidate].terms:
                        documents.append(candidate)
            return documents

        query_representation = self.model.query_to_representation(query)
        queries=[query_representation]
        for qr in queries:
            try:
                parsed_query = expr.parseString(qr)
                retrieved_documents=list(compute_expression_from_collection(parsed_query))
            
                results=[]
                for d in self.collection:
                    if d.document_id in retrieved_documents:
                        results.append((1.0,d))
                results=sorted(results, key=lambda x: x[0], reverse=True)
                return results
            except:
                results=[]
                return results

    def calculate_precision(self,query: str, result_list: list[tuple]) -> float:
        
        def compute_expression_from_ground_truth(expression)->set:

            result_set=set()
            last_operator=None
            is_negation=False
            for element in expression:
                if isinstance(element,pyparsing.results.ParseResults):
                    current_group_set=compute_expression_from_ground_truth(element)
                    if is_negation:
                        union_set=set([d.document_id for d in self.collection])
                        
                        current_group_set=union_set.difference(current_group_set)
                        
                        is_negation=False
                    
                    if len(result_set)>0:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_group_set)
                            
                        elif last_operator=='|':
                            result_set=result_set.union(current_group_set)
                    else:
                        result_set=current_group_set
                    continue
                    
                if element not in ['&','|']:
                    if element=='-':
                        is_negation=True
                        continue
                    
                    current_term=element
                    current_term_set=set(gt_search_terms[porter.stem_term(current_term)])
                    if is_negation:
                       
                        union_set=set([d.document_id for d in self.collection])
                        current_term_set=set(gt_search_terms[porter.stem_term(current_term)])
                        
                        current_term_set=union_set.difference(current_term_set)
                        is_negation=False
                    
                    if last_operator is None and len(result_set)==0:
                        result_set=current_term_set
                    else:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_term_set)
                        elif last_operator=='|':
                            result_set=result_set.union(current_term_set)
                            
                else:
                    last_operator=element
            return result_set
        gt_file_path=os.path.join(RAW_DATA_PATH, 'ground_truth.txt')
        with open(gt_file_path,'r') as f:
            gt_file=f.readlines()
        gt_search_terms={}
        for row in gt_file:
            if row=='\n':
                break
            term=row.split('-')[0].strip()
            relevant_docs=row.split('-')[1].strip().split(', ')
            relevant_docs=[int(id)-1 for id in relevant_docs]
            gt_search_terms[porter.stem_term(term)]=relevant_docs
        
        query_representation = self.model.query_to_representation(query)
        if not isinstance(self.model,models.VectorSpaceModel):
            queries=[query_representation]
            for qr in queries:
                try:
                    parsed_query = expr.parseString(qr)
                    retrieved_gt_documents=list(compute_expression_from_ground_truth(parsed_query))
                    if len(set(retrieved_gt_documents))==0:
                        return -1
                    retrieved_query_documents=[]
                    for doc in result_list:
                        if doc[0]==1.0:
                            retrieved_query_documents.append(doc[1].document_id) 
                    if len(set(retrieved_query_documents))==0:
                        return 0.0
                    return len(set(retrieved_gt_documents).intersection(set(retrieved_query_documents)))/len(set(retrieved_query_documents))
                except:
                    return -1
        else:
            try:
                query_terms=query_representation.split(' ')
                gt_relevant_documents=set()
                for t in query_terms:
                    gt_relevant_documents=gt_relevant_documents.union(set(gt_search_terms[porter.stem_term(t)]))
                gt_relevant_documents=list(gt_relevant_documents)
        
                if len(gt_relevant_documents)==0:
                    return -1
                
                precision=0.0
                relevant_docs=0
                for i in range(len(result_list)):
                    if result_list[i][1].document_id in gt_relevant_documents:
                        relevant_docs+=1
                    precision=relevant_docs/(i+1)
                
                return precision
            except:
                return -1
            



        
            



        
        

    def calculate_recall(self,query: str, result_list: list[tuple]) -> float:
        
        def compute_expression_from_ground_truth(expression)->set:

            result_set=set()
            last_operator=None
            is_negation=False
            for element in expression:
                if isinstance(element,pyparsing.results.ParseResults):
                    current_group_set=compute_expression_from_ground_truth(element)
                    if is_negation:
                        union_set=set([d.document_id for d in self.collection])
                        
                        current_group_set=union_set.difference(current_group_set)
                        
                        is_negation=False
                    
                    if len(result_set)>0:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_group_set)
                            
                        elif last_operator=='|':
                            result_set=result_set.union(current_group_set)
                    else:
                        result_set=current_group_set
                    continue
                if element not in ['&','|']:
                    if element=='-':
                        is_negation=True
                        continue
                    
                    current_term=element
                    if is_negation:
                      
                        union_set=set([d.document_id for d in self.collection])
                        current_term_set=set(gt_search_terms[porter.stem_term(current_term)])
                        
                        current_term_set=union_set.difference(current_term_set)
                        is_negation=False
                    else:
                        current_term_set=set(gt_search_terms[porter.stem_term(current_term)])
                    
                    
                    if last_operator is None and len(result_set)==0:
                        result_set=current_term_set
                    else:
                        if last_operator=='&':
                            result_set=result_set.intersection(current_term_set)
                        elif last_operator=='|':
                            result_set=result_set.union(current_term_set)             
                            
                else:
                    last_operator=element
            return result_set
        gt_file_path=os.path.join(RAW_DATA_PATH, 'ground_truth.txt')
        with open(gt_file_path,'r') as f:
            gt_file=f.readlines()
        gt_search_terms={}
        for row in gt_file:
            if row=='\n':
                break
            term=row.split('-')[0].strip()
            relevant_docs=row.split('-')[1].strip().split(', ')
            relevant_docs=[int(id)-1 for id in relevant_docs]
            gt_search_terms[porter.stem_term(term)]=relevant_docs
        
        query_representation = self.model.query_to_representation(query)
        if not isinstance(self.model,models.VectorSpaceModel):
            queries=[query_representation]
            for qr in queries:
                try:
                    parsed_query = expr.parseString(qr)
                    retrieved_gt_documents=list(compute_expression_from_ground_truth(parsed_query))
                    if len(set(retrieved_gt_documents))==0:
                        return -1
                    retrieved_query_documents=[]
                    for doc in result_list:
                        if doc[0]==1.0:
                            retrieved_query_documents.append(doc[1].document_id) 
                    if len(set(retrieved_query_documents))==0:
                        return 0.0
                    return len(set(retrieved_gt_documents).intersection(set(retrieved_query_documents)))/len(set(retrieved_gt_documents))
                except:
                    return -1
        else:
            try:
                query_terms=query_representation.split(' ')
                gt_relevant_documents=set()
                for t in query_terms:
                    gt_relevant_documents=gt_relevant_documents.union(set(gt_search_terms[porter.stem_term(t)]))
                gt_relevant_documents=list(gt_relevant_documents)
                
                if len(gt_relevant_documents)==0:
                    return -1
                if len(result_list)==0:
                    return 0.0
                recall_values=[0.0]*len(result_list)
                step_size=1/len(gt_relevant_documents)

                if result_list[0][1] in gt_relevant_documents:
                    recall_values[0]=step_size
                
                for i in range(1,len(recall_values)):
                    if result_list[i][1].document_id in gt_relevant_documents:
                        recall_values[i]=recall_values[i-1]+step_size
                    else:
                        recall_values[i]=recall_values[i-1]
    
                return recall_values[-1]
            except:
                return -1


if __name__ == '__main__':
    irs = InformationRetrievalSystem()
    irs.main_menu()
    exit(0)
