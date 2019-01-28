################### LIBRARY IMPORTS ################### 

import requests
import json
import os
import time
import numpy as np 
import pandas as pd

################### SOME DEFAULT PARAMETERS ################### 

DEFAULT_OPTIONS = {'resultType':'core','pageSize':'1000',
                   'format':'json'}
                   
API_BASE = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query='

CITATIONS_BASE = 'https://www.ebi.ac.uk/europepmc/webservices/rest/MED/'
CITATIONS_OPTIONS = {'pageSize':'1000', 'format':'json'}


################### FUNCTIONS TO PERFORM API QUERIES ################### 

def query(query_str, base_url=API_BASE, options=DEFAULT_OPTIONS, 
          cursorMark='*',cursorStr='cursorMark'):
    '''
    Perform one query of the EPMC search API.
    * query_str (str): string of query terms.
    * base_url (str): URL up to point where query terms will be appended.
    * options (dict): dictionary of option name (str):option value (str) pairs to append to url after the query string.
    * cursorMark (str): cursor value identifying which page to return.
    * cursorStr (str): cursor parameter name
    '''
    
    if query_str[-1]=='?':
        query_full_url = base_url + query_str + build_options(options)[1:] # skip leading &
    else:
        query_full_url = base_url + query_str + build_options(options) # don't skip leading &
    
    query_full_url = query_full_url + '&' + cursorStr + '=' + str(cursorMark)  
    
    response = requests.get(query_full_url)
    response = response.json()
    
    return response

def query_all_pages(query_str, save_name,
                    base_url=API_BASE, options=DEFAULT_OPTIONS,
                    save_dir='data/EPMC/json',
                    cursorStr='cursorMark',
                    cursorKey='nextCursorMark',
                    firstCursorMark = '*',
                    resultKeys = ['resultList','result'],
                    n_attempts=10,time_between_requests=1):
    '''
    Query and save all pages of an EPMC search API request.
    * query_str (str): string of query terms.
    * save_name (str): file name prefix
    * base_url (str): URL up to point where query terms will be appended.
    * options (dict): dictionary of option name (str):option value (str) pairs to append to url after the query string.
    * save_dir (str): directory to save json response files.
    * cursorStr (str): cursor parameter name (for page number)
    * cursorKey (str): response field to find next page number to query
    * firstCursorMark (str): str identifying first page to query
    * resultKeys (list): name of fields to find results in each response
    * n_attempts (int): how many times to attempt each API request.
    * time_between_requests (int): how many seconds to wait between requests.
    '''
    
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)

    
    nextCursorMark = firstCursorMark
    page_number = 0
    n_results = 0
    failed_count = 0
    n_response = 999999
    hit_count = 999999
    response_list = []
    
    while (n_results<hit_count) and (n_response>0):
        if failed_count==0:
            print('Querying page '+str(page_number+1)+': ',end='')

        try:
            response = query(query_str,base_url,options,
                            cursorMark=nextCursorMark, cursorStr=cursorStr)
            
            if cursorKey=='page':
                nextCursorMark = response['request']['page']+2
            else:
                nextCursorMark = response[cursorKey]
    
            n_response = len(response[resultKeys[0]][resultKeys[1]])
            n_results = n_results + n_response
            hit_count = response['hitCount']
            
            print(hit_count,'hits total,',n_response,'in this page,',n_results,'collected so far.')

        
        except:
            if failed_count>=n_attempts:
                print("FAILED.")
            else:
                failed_count = failed_count+1
                time.sleep(time_between_requests)
                continue
        
        page_number = page_number+1
        
        if failed_count<n_attempts:
            if save_name is None:
                response_list.append(response)
            else:
                file_name = save_dir+'/'+save_name+'_page'+str(page_number).zfill(6)+'.json'
                
                if n_response>0:
                    with open(file_name,'w') as f:
                        json.dump(response,f)

        failed_count = 0
            
        time.sleep(time_between_requests)
        
    if save_name is None:
        return response_list

def query_citations(pmids, save_dir,
                    n_attempts=10,time_between_requests=1):
    '''
    Query and save json for all papers citing the papers in pmids.
    * pmids (str or list): publication PMIDs to obtain citations for.
    * save_dir (str): directory to save json response files.
    * n_attempts (int): how many times to attempt each API request.
    * time_between_requests (int): how many seconds to wait between requests.
    '''
    

    if type(pmids) is not list:
        pmids = [pmids]
        
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)

    for idx,pmid in enumerate(pmids):
        pmid = str(pmid)
        print('Querying PMID '+pmid+' ('+str(idx+1)+' out of '+str(len(pmids))+'): ')
        
        query_str = pmid + '/citations?'
        
        n_citations = 0

        response_list = query_all_pages(query_str, save_name=None,
                                        base_url=CITATIONS_BASE,
                                        options=CITATIONS_OPTIONS,
                                        cursorStr='page',
                                        cursorKey='page',
                                        firstCursorMark = '1',
                                        resultKeys = ['citationList','citation'],
                                        n_attempts=n_attempts,
                                        time_between_requests=time_between_requests)
        
        try:
            n_citations = response_list[0]['hitCount']  
            print('Returned',n_citations,'citations.')
        
        except:
            print('FAILED.')
            continue
        
        if n_citations>0:
            print('Getting meta data for cited papers...')
            
            citation_pmids = [citation['id'] for response in response_list for citation in response['citationList']['citation']]
            
            if len(citation_pmids)>300:
                print('Large number of citations: Splitting to multiple queries.')
                start_idx = 0
                n_queries = 0
                while start_idx+300 < len(citation_pmids):
                    n_queries = n_queries+1
                    print('QUERY '+str(n_queries))
                    
                    end_idx = start_idx+300
                    
                    if end_idx>len(citation_pmids):
                        end_idx = len(citation_pmids)
                        
                    pmids_to_query = citation_pmids[start_idx:end_idx]
                    
                    query_str = build_OR_query(pmids_to_query) 
                    
                    save_name = 'PMID_'+pmid+'_citations_query' + str(n_queries).zfill(3)
                    
                    query_all_pages(query_str, save_name, save_dir=save_dir,
                                    n_attempts=n_attempts,
                                    time_between_requests=time_between_requests)
                    
                    start_idx=start_idx+300
                    
            else:
                query_str = build_OR_query(citation_pmids) 
                
                save_name = 'PMID_'+pmid+'_citations'
                
                query_all_pages(query_str, save_name, save_dir=save_dir,
                                n_attempts=n_attempts,
                                time_between_requests=time_between_requests)
        
        print('-------------------------------------------')
        time.sleep(time_between_requests)
        

def get_citations(pmids, save_dir, save_name,
                  n_attempts=10,time_between_requests=0.05):
    '''
    Query and save ids of all papers citing a paper in pmids.
    '''
    
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)

    citations = pd.Series(index=pmids)
    citations.index = citations.index.astype(str)
    
    for idx,pmid in enumerate(pmids):
        pmid = str(pmid)
        print('Querying PMID '+pmid+' ('+str(idx+1)+' out of '+str(len(pmids))+'): ')
        
        query_str = pmid + '/citations?'
        
        n_citations = 0

        response_list = query_all_pages(query_str, save_name=None,
                                        base_url=CITATIONS_BASE,
                                        options=CITATIONS_OPTIONS,
                                        cursorStr='page',
                                        cursorKey='page',
                                        firstCursorMark = '1',
                                        resultKeys = ['citationList','citation'],
                                        n_attempts=n_attempts,
                                        time_between_requests=time_between_requests)
        
        try:
            n_citations = response_list[0]['hitCount']  
            print('Returned',n_citations,'citations.')
        
        except:
            print('FAILED.')
            continue
        
        if n_citations>0:
            citation_pmids = [citation['id'] for response in response_list for citation in response['citationList']['citation']]
            
            citations[pmid] = citation_pmids
        
        print('-------------------------------------------')
        time.sleep(time_between_requests)

    citations.to_csv(save_dir+'/'+save_name+'.csv')
    citations.to_pickle(save_dir+'/'+save_name+'.pkl')

################### FUNCTIONS TO BUILD QUERY STRINGS ################### 
        
def build_options(options_dict):
    '''
    Convert options_dict into a string of & separated option=value pairs.
    '''
    options_str = ''
    
    for key,value in options_dict.items():
        options_str = options_str + '&'+key+'='+value

    return options_str

def build_OR_query(terms):
    '''
    Convert terms (list) into an OR separated query string.
    '''

    query_str = ''
    
    for term in terms:
        query_str = query_str + '"' + term + '" OR '
    
    query_str = query_str[:-4]
    
    return query_str
    
def build_AND_query(terms):
    '''
    Convert terms (list) into an AND separated query string.
    '''
    query_str = ''
    for term in terms:
        query_str = query_str+'('+term+') AND '
        
    query_str = query_str[:-5]
    
    return query_str
    
def build_date_query(start_date,end_date='2020-12-31'):
    '''
    Convert start_date and end_date (str) into a first publication date query string.
    '''
    query_str = 'FIRST_PDATE:['+start_date+' TO '+end_date+']'

    return query_str

def build_field_OR_query(fields,terms):
    '''
    Convert terms (list) into an OR separated query string in a specific field.
    '''
    if type(fields) is not list:
        fields = [fields]
        
    if type(terms) is not list:
        terms = [terms]
    
    query_str = ''
    
    for term in terms:
        for field in fields:
            query_str = query_str + field + ':"' + term + '" OR '
    
    query_str = query_str[:-4]
    
    return query_str
    
def build_field_query(field,query_str):
    '''
    Add field name to a query string, to limit that query to a specific field.
    '''
    return field+':"'+query_str+'"'
    
################### FUNCTIONS TO CONVERT JSONS TO DATAFRAMES ################### 

def combine_jsons_to_df(json_paths, 
                        file_col_name=None, file_col_values=None):
    df_list = []
    #df = None
    
    for idx,path in enumerate(sorted(json_paths)):
        print(idx+1,'out of',len(json_paths),':',path)
        with open(path,'r') as f:
            response = json.loads(f.read())
        
        new_df = json_to_df(response)
        
        if (file_col_name is not None) and (file_col_values is not None):
            new_df[file_col_name] = file_col_values[idx]
        
        #if df is None:
        #    df = new_df.copy()
        #else:
        #    df = pd.concat([df,new_df], ignore_index=True, sort=False)
        df_list.append(new_df)
        
    df = pd.concat(df_list, ignore_index=True, sort=False)
    
    # pandas duplicates can't deal with dicts so convert everything to str for check
    df = df[~df.astype(str).duplicated()].reset_index(drop=True)
    
    return df

def json_to_df(response, 
               columns=['abstractText','authorList','chemicalList',
                        'citedByCount','doi','firstPublicationDate',
                        'grantsList','id','journalInfo',
                        'keywordList','meshHeadingList','pmcid',
                        'pmid','pubYear','title']):
                            
    '''convert a single json response from the EPMC search API into a
    pandas data frame. Any length 1 dictionaries or lists found in the
    resulting columns are flattened.'''
    
    df = pd.DataFrame(response['resultList']['result'])
    df = df[[col for col in columns if df.columns.contains(col)]]
    
    for col in df.columns:
        
        # flatten length 1 dictionaries
        is_dict = [type(x) is dict for x in df[col]]
        
        if sum(is_dict)>0:
            len1_dict = [len(x)==1 for x in df.loc[is_dict,col]]
            
            if all(len1_dict):
                def extract_key_from_dict(the_dict):
                    if (type(the_dict) is dict) and (len(the_dict)==1):
                        key = list(the_dict.keys())
                        key = key[0]
                        return the_dict[key]
                        
                    else:
                        return the_dict
            
                df[col] = df[col].apply(extract_key_from_dict)

        # flatten length 1 lists
        is_list = [type(x) is list for x in df[col]]
        
        if sum(is_list)>0:
            len1_list = [len(x)==1 for x in df.loc[is_list,col]]
            
            if all(len1_list):
                def flatten_list(the_list):
                    if (type(the_list) is list) and (len(the_list)==1):
                        return the_list[0]
                        
                    else:
                        return the_list
            
                df[col] = df[col].apply(flatten_list)
       
    return df