# Contains all functions related to the porter stemming algorithm.

from document import Document
import re

def get_measure(term: str) -> int:
    """
    Returns the measure m of a given term [C](VC){m}[V].
    :param term: Given term/word
    :return: Measure value m
    """
    term=term.upper()
    vowels=['A','E','I','O','U']
    is_vowel_found=False
    term_measure=0
    for i in range(len(term)):
        if term[i] in vowels:
            is_vowel_found=True
        else:
            if term[i]=='Y':
                if i-1>=0:
                    if term[i-1] not in vowels or not is_vowel_found:
                        is_vowel_found=True
                    else:
                        if is_vowel_found==True:
                            term_measure+=1
                        is_vowel_found=False

            else:
                if is_vowel_found==True:
                    term_measure+=1
                is_vowel_found=False
    return term_measure


def condition_v(stem: str) -> bool:
    """
    Returns whether condition *v* is true for a given stem (= the stem contains a vowel).
    :param stem: Word stem to check
    :return: True if the condition *v* holds
    """
    stem=stem.upper()
    vowels=['A','E','I','O','U']
    is_vowel_found=False
    for i in range(len(stem)):
        if stem[i] in vowels:
            return True
        else:
            if stem[i]=='Y':
                if i-1>=0:
                    if stem[i-1] not in vowels or not is_vowel_found:
                        return True
                    else:
                        is_vowel_found=False

            else:
                is_vowel_found=False
    return False


def condition_d(stem: str) -> bool:
    """
    Returns whether condition *d is true for a given stem (= the stem ends with a double consonant (e.g. -TT, -SS)).
    :param stem: Word stem to check
    :return: True if the condition *d holds
    """
    stem=stem.upper()
    pattern='[^AEIOU]{2}$'
    if re.search(pattern,stem) and stem[-1]==stem[-2]:
        return True
    
    return False


def cond_o(stem: str) -> bool:
    """
    Returns whether condition *o is true for a given stem (= the stem ends cvc, where the second c is not W, X or Y
    (e.g. -WIL, -HOP)).
    :param stem: Word stem to check
    :return: True if the condition *o holds
    """
    stem=stem.upper()
    vowels=['A','E','I','O','U']
    is_vowel_found=False
    vowels_consonants_occurrences=''
    for i in range(len(stem)):
        if stem[i] in vowels:
            is_vowel_found=True
        else:
            if stem[i]=='Y':
                if i-1>=0:
                    if stem[i-1] not in vowels or not is_vowel_found:
                        is_vowel_found=True
                    else:
                    
                        is_vowel_found=False

            else:
                is_vowel_found=False
        if is_vowel_found:
            vowels_consonants_occurrences+='1'
        else:
            vowels_consonants_occurrences+='0'
    
    if len(vowels_consonants_occurrences)>=3:
        if vowels_consonants_occurrences[-3]=='0' and vowels_consonants_occurrences[-2]=='1' and vowels_consonants_occurrences[-1]=='0' and stem[-1] not in ['W','X','Y']:
            return True
        return False

    else:
        return False


def stem_term(term: str) -> str:
    """
    Stems a given term of the English language using the Porter stemming algorithm.
    :param term:
    :return:
    """

    term=term.upper()
    def step_1a(term):
        patterns=['SSES$','IES$','SS$','S$']
        replacements=['SS','I','SS','']
        for pattern,repl in zip(patterns,replacements):
            if re.search(pattern,term):
                term=re.sub(pattern,repl,term)
                return term
        return term
    def step_1b(term):

        pattern='EED$'
        if re.search(pattern,term):

            stem=term[:re.search(pattern,term).span()[0]]
            if get_measure(stem)>0:
                term=re.sub(pattern,'EE',term)
                return term
        pattern='ED$'
        if re.search(pattern,term):
            stem=term[:re.search(pattern,term).span()[0]]
            if condition_v(stem):
                term=re.sub(pattern,'',term)
            
                if re.search('AT$',term):
                    term=re.sub('AT$','ATE',term)
                    return term
                if re.search('BL$',term):
                    term=re.sub('BL$','BLE',term)
                    return term
                if re.search('IZ$',term):
                    term=re.sub('IZ$','IZE',term)
                    return term

                if condition_d(term) and not (re.search('LL$',term) or re.search('SS$',term) or re.search('ZZ$',term)):
                    term=re.sub(term[-2]+term[-1]+'$',term[-2],term)
                    return term
                return term
           

            
        pattern='ING$'
        if re.search(pattern,term):
            stem=term[:re.search(pattern,term).span()[0]]
            if condition_v(stem):
                term=re.sub(pattern,'',term)
                if condition_d(term) and not (re.search('LL$',term) or re.search('SS$',term) or re.search('ZZ$',term)):
                    term=re.sub(term[-2]+term[-1]+'$',term[-2],term)
                    return term
                if get_measure(term)==1 and cond_o(term):
                    term=term+'E'
                    return term
                return term
        return term
    def step_1c(term):
        pattern='Y$'
        if re.search(pattern,term):
            stem=term[:re.search(pattern,term).span()[0]]
            if condition_v(stem):
                term=re.sub(pattern,'I',term)
                return term
        return term
    def step_2(term):
        patterns=['ATIONAL','TIONAL','ENCI','ANCI','IZER','ABLI','ALLI','ENTLI','ELI','OUSLI','IZATION','ATION','ATOR','ALISM','IVENESS','FULNESS','OUSNESS','ALITI','IVITI','BILITI','XFLURTI']
        replacements=['ATE','TION','ENCE','ANCE','IZE','ABLE','AL','ENT','E','OUS','IZE','ATE','ATE','AL','IVE','FUL','OUS','AL','IVE','BLE','XTI']    
        for pattern,repl in zip(patterns,replacements):
            if re.search(pattern+'$',term):
                stem=term[:re.search(pattern+'$',term).span()[0]]
                if get_measure(stem)>0:
                    term=re.sub(pattern+'$',repl,term)
                    return term
        return term
    def step_3(term):
        patterns=['ICATE','ATIVE','ALIZE','ICITI','ICAL','FUL','NESS']
        replacements=['IC','','AL','IC','IC','','']    
        for pattern,repl in zip(patterns,replacements):
            if re.search(pattern+'$',term):
                stem=term[:re.search(pattern+'$',term).span()[0]]
                if get_measure(stem)>0:
                    term=re.sub(pattern+'$',repl,term)
                    return term
        return term
        
    def step_4(term):
        patterns=['AL','ANCE','ENCE','ER','IC','ABLE','IBLE','ANT','EMENT','MENT','ENT','OU','ISM','ATE','ITI','OUS','IVE','IZE']
        replacements=['']*len(patterns)

        for pattern,repl in zip(patterns,replacements):
            if re.search(pattern+'$',term):
                stem=term[:re.search(pattern+'$',term).span()[0]]
                if get_measure(stem)>1:
                    term=re.sub(pattern+'$',repl,term)
                    return term
        pattern='ION$'
        if re.search(pattern,term):

            stem=term[:re.search(pattern,term).span()[0]]
            if (stem[-1]=='S' or stem[-1]=='T') and get_measure(stem)>1:
                term=re.sub(pattern,'',term)
                return term
        return term
    
    def step_5a(term):
        pattern='E$'
        if re.search(pattern,term):

            stem=term[:re.search(pattern,term).span()[0]]
            if get_measure(stem)>1:
                term=re.sub(pattern,'',term)
                return term
            if get_measure(stem)==1 and not cond_o(stem):
                term=re.sub(pattern,'',term)
                return term
        
        return term
    def step_5b(term):
        if condition_d(term) and get_measure(term)>1 and term[-1]=='L':
            term=re.sub('LL$','L',term)
            return term
        return term
    
    term=step_1a(term)

    term=step_1b(term)
    
    term=step_1c(term)

    term=step_2(term)

    term=step_3(term)
    
    term=step_4(term)
    
    term=step_5a(term)

    term=step_5b(term)
    
    term=term.lower()
    return term

def stem_all_documents(collection: list[Document]):
    """
    For each document in the given collection, this method uses the stem_term() function on all terms in its term list.
    Warning: The result is NOT saved in the document's term list, but in the extra field stemmed_terms!
    :param collection: Document collection to process
    """
    for i in range(len(collection)):
        for j in range(len(collection[i].terms)):
            collection[i].stemmed_terms.append(stem_term(collection[i].terms[j]))
    


def stem_query_terms(query: str) -> str:
    """
    Stems all terms in the provided query string.
    :param query: User query, may contain Boolean operators and spaces.
    :return: Query with stemmed terms
    """
    terms=re.findall('\w+',query)
    for term in terms:
        query=re.sub(term,stem_term(term),query)
    
    return query
