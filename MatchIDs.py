import pandas as pd
import numpy as np

def find_matches_in_master(df, 
                           master_path='data/Award Holders Master.xlsx',
                           check_cols=['Grant number', 'Grant number.1',
                                       'Finance Reference','Grant Ref Unique']):
                                           
    '''Searches the index of df for matches in the master spreadsheet, returns
    df with a new column MasterID to identify the corresponding entry in master.'''

    # dat frame of references converted from format '1234/56' to lists like ['1234','56']
    split_idx = pd.DataFrame(df.index.str.split('/').tolist(),
                                columns=['ref1','ref2'],index=df.index)
    
    # if had format '1234/56' add prefix to second number from first to get ['1234','1256'].
    # references starting with U start with 24 in Award Master.
    def add_prefix(row):
        if (row['ref2'] is not None) and len(row['ref2'])==2:
            row['ref2'] = row['ref1'][:2]+row['ref2']
            
        elif (row['ref2'] is not None) and len(row['ref2'])==1:
            row['ref2'] = row['ref1'][:3]+row['ref2']
            
        if (row['ref1'][0]=='U'):
            row['ref1'] = '24'+row['ref1'].replace('U','')
        
        return row
    
    
    split_idx = split_idx.apply(add_prefix,axis=1)
    
    # remove nan or duplicated indices
    split_idx = split_idx[~split_idx.index.isnull()]
    split_idx = split_idx[~split_idx.index.duplicated()]

    
    master = pd.read_excel(master_path)
    
    # isin: array to contain whether each research grant has been found in
    # the master spreadsheet. Initialise as false
    isin = pd.Series(False,index=split_idx.index)
    
    # column to store corresponding Master IDs
    df['MasterID'] = np.nan
    
    for col in check_cols:
        master_col = master[col].astype(str)
        
        ref1_isin = split_idx['ref1'].isin(master_col)
        ref2_isin = split_idx['ref2'].isin(master_col)
    
        isin = isin | ref1_isin
        isin = isin | ref2_isin
        
        # for rows that don't have MasterID assigned, check for new matches
        row_ids = df[df['MasterID'].isnull()].index
        for row in row_ids:
            if ref1_isin[row].any():
                df.loc[row,'MasterID'] = master.loc[master_col==split_idx.loc[row,'ref1'],
                                                          'Grant Ref Unique'].iloc[0]
            elif ref2_isin[row].any():
                df.loc[row,'MasterID'] = master.loc[master_col==split_idx.loc[row,'ref2'],
                                                          'Grant Ref Unique'].iloc[0]
    
    print('Found',df['MasterID'].nunique(),'matches in master.')
    print(sum(~isin),'grants were not found in master:')
    print(split_idx[~isin].sort_index().index.tolist())
    
    return df