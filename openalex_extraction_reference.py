# openalex credentials

# No credentials are needed.

# ----------------------------------------------------------------------------
# Load libraries
import requests
import pandas as pd
import time
import random
import os
import pickle

# ----------------------------------------------------------------------------
# mount my google drive
from google.colab import drive
drive.mount('/content/drive')

# ----------------------------------------------------------------------------
# Folder to save the results
DATAFOLDER = "drive/MyDrive/Test"

# ----------------------------------------------------------------------------
# # Query. Term search
# KEYWORDS = '''
#   ("energy storage" OR "energy harvesting" OR "supercapacitor" OR "pseudocapacitor")
# '''
# #patent* AND ("artificial intelligence" OR "machine learning")
# #@markdown The start/end year of publications used to extract patents
# YEAR_START = 2015 #@param {type: "slider", min: 1950, max: 2023}
# YEAR_END = 2025  #@param {type: "slider", min: 1950, max: 2023}

# if YEAR_END < YEAR_START:
#   YEAR_END = YEAR_START

# ----------------------------------------------------------------------------
# # Journals: First find the id of the journal
# # https://docs.openalex.org/api-entities/sources/filter-sources
# journal_endpoint = "https://api.openalex.org/sources"
# journal_q = "ieee"
# response = requests.get(f'{journal_endpoint}?search={journal_q}&select=id,issn,display_name,works_count,cited_by_count,alternate_titles')
# #response.json()
# pd.json_normalize(response.json()['results']).head()

# ----------------------------------------------------------------------------
# test = pd.json_normalize(response.json()['results'])
# test = test['id'].apply(lambda x: x.replace('https://openalex.org/', ''))
# ieee_ids = list(set(test.to_list()))
# ieee_ids

# ----------------------------------------------------------------------------
# Query. Advanced search

# # comma separated list of ISO 2-digit codes
# countries = ["JP","US"]

# # comma separated list of openalex ids
# institutions = []
# authors = []
# journals = ieee_ids

# # Other filters allowed by openalex
# # numeric filters are = > <. Not possible with ">=" or "=<"
#advanced = 'cited_by_count:>100'

# ----------------------------------------------------------------------------
# Create the folder if doesn't exists
if not os.path.exists(DATAFOLDER):
  !mkdir $DATAFOLDER
  print(f"==\nCreated data folder:", DATAFOLDER + "/")

# ----------------------------------------------------------------------------
# New format query 20250416

# Format term search query to openalex syntax
def format_query_openalex(search_terms):
  return f'title_and_abstract.search:{search_terms}'

# ----------------------------------------------------------------------------
# create query string
def create_query_string_for_openalex(keywords, from_year, to_year, countries=[], authors=[], institutions=[], journals=[], advanced=''):
  '''
  Creates the query string used to call openalex.
  Printing this string and put it in a browser should work.
  '''
  main_string = []

  # Works endpoint
  works_endpoint = "https://api.openalex.org/works"

  # Add user input
  if keywords.strip() != '':
    main_string.append(format_query_openalex(keywords))
  if from_year != '':
    main_string.append(f'from_publication_date:{from_year}-01-01')
  if to_year != '':
    main_string.append(f'to_publication_date:{to_year}-12-31')
  if type(countries) == type([]) and countries != []:
    main_string.append(f"institutions.country_code:{'|'.join(countries)}")
  if type(authors) == type([]) and authors != []:
    main_string.append(f"authorships.author.id:{'|'.join(authors)}")
  if type(institutions) == type([]) and institutions != []:
    main_string.append(f"institutions.id:{'|'.join(institutions)}")
  if type(journals) == type([]) and journals != []:
    main_string.append(f"locations.source.id:{'|'.join(journals)}")
  if type(advanced) == type('') and advanced != '':
    advanced = advanced.replace('\n','').strip()
    main_string.append(advanced)

  # Add hardcoded filters
  paper_type = 'type:article'
  #language = 'language:en'
  #retracted = 'is_retracted:false'

  main_string.append(paper_type)
  #main_string.append(language)
  #main_string.append(retracted)
  main_string = ','.join(main_string)

  # Other query parameters
  # Sorting
  sorting = 'cited_by_count:desc'

  # Select
  selection = 'id,doi,title,publication_year,language,type,primary_location,open_access,authorships,cited_by_count,referenced_works,abstract_inverted_index,concepts,is_retracted'

  # Authentication
  email = f"mailto={random.choice(('cristian@jiyu-labs.com','admin@jiyu-labs.com'))}"

  # Full query
  full_query = f'{works_endpoint}?filter={main_string}&sort={sorting}&select={selection}&{email}'

  return full_query

# ----------------------------------------------------------------------------
def download_from_openalex(formatted_query, records_per_call = 200, pause_time = 1):
  '''
  Iteratively download the records from Open Alex.
  formatted_query: is the output from `create_query_string_for_openalex()`
  records_per_call: the number of papers to download per API call. The max allowed is 200. If the server report errors or becomes slow use a lower value
  pause_time: Open Alex is a public service, to not overload their server we pasue between calls.
  '''
  # Pagination
  per_page = records_per_call #The max is 200.
  cursor = '*' #The first page is always '*' in cursor pagination

  # Loop for downloading the records.
  papers = []
  while cursor is not None:
    loop_query = f'{formatted_query}&per-page={per_page}&cursor={cursor}'
    response = requests.get(loop_query)
    print(response.json()['meta'])
    papers = papers + response.json()['results']
    cursor = response.json()['meta']['next_cursor']
    time.sleep(max(0.5, pause_time))

  return papers

# ----------------------------------------------------------------------------
def format_abstract(abstract_inverted_index):
  ''' Takes an abstract inverted index from OpenAlex and transforms it to regular text'''
  word_index = []
  if (abstract_inverted_index is not None) and (len(abstract_inverted_index) > 0):
    for k,v in abstract_inverted_index.items():
      for index in v:
        word_index.append([k,index])
    word_index = sorted(word_index,key = lambda x : x[1])
  return(' '.join([i[0] for i in word_index]))

# ----------------------------------------------------------------------------
def format_concepts(concepts):
  '''takes the concept object from Open Alex and transform it to a list as in Dimensions.
     Open Alex concepts have a score. We take those with a score >=0.3'''
  formatted_concepts = []
  if len(concepts) > 0:
    formatted_concepts = [concept['display_name'] for concept in concepts if concept['score'] >= 0.3]
  return formatted_concepts

# ----------------------------------------------------------------------------
def format_journal(primary_location, doi, infer = False):
  '''takes the primary location dictionary and format it in the JSON expected by dimensions'''
  formatted_journal = {'id': '', 'title': ''}
  if (primary_location is not None) and (isinstance(primary_location, dict)) and ('source' in primary_location.keys()):
    if primary_location['source'] is not None:
      #print('Formatting journal name with provided openalex data')
      formatted_journal = {
                            'id': primary_location['source']['id'],
                            'title': primary_location['source']['display_name']
                          }
    else:
      if (infer) and (doi is not None):
        print(f'Finding journal name from Crossref for doi: {doi}')
        #print(primary_location['source'])
        try:
          crossref_response = requests.get(f'https://api.crossref.org/works?filter=doi:{doi.replace("https://doi.org/","")}&select=short-container-title&mailto=cristianmejia00@gmail.com')
          journal_name = crossref_response.json()['message']['items'][0]['short-container-title'][0]
        except Exception as e:
          print(e)
          journal_name = ''
        finally:
          formatted_journal = {
                        'id': journal_name,
                        'title': journal_name
          }
  return formatted_journal

# ----------------------------------------------------------------------------
def find_if_open_access(primary_location):
  is_oa = {}
  if (primary_location is not None) and (isinstance(primary_location, dict)) and ('is_oa' in primary_location.keys()):
    is_oa = {
        'is_oa': primary_location['is_oa'],
        'oa_pdf': primary_location['pdf_url']
    }
  return is_oa

# ----------------------------------------------------------------------------
country_codes = pd.read_csv("https://raw.githubusercontent.com/cristianmejia00/display/refs/heads/main/ISO3166_country_codes.csv")
iso_country = {}
for i in range(0,len(country_codes)):
  iso_country[country_codes['alpha_2_code'][i]] = country_codes['country'][i]
country_codes.head()

# ----------------------------------------------------------------------------
def format_authorship(authorships):
  '''
  Takes the authorships object from openalex and extracts the authors, institutions, and countries in the format expected by dimensions.
  '''
  institutions = []
  countries = []
  authors = []
  if (authorships is not None) and (len(authorships) > 0):
    for i in authorships:
      try:
        authors.append({'last_name': i['author']['display_name']})
      except KeyError as e:
        print(e)
      for j in i['institutions']:
        try:
          institutions.append(j['display_name'])
        except KeyError as e:
          print(e)
        try:
          if j['country_code'] is not None:
            countries.append(iso_country[j['country_code'].upper()])
        except KeyError as e:
          print(e)
  else:
    authors = []
  institutions = list(set(institutions))
  countries = list(set(countries))
  return authors, institutions, countries

# ----------------------------------------------------------------------------
def sanitize_openalex_json(paper):
  '''
  Verify that every downloaded record has all necessary fields.
  When missing, we add properly formatted empty strings.
  This function allows avoinding the `KeyError` further down the road.
  '''
  # Every oap must have these keys
  if 'authorships' not in paper.keys():
    paper['authorships'] = []
  if 'id' not in paper.keys():
    paper['id'] = f'missing_oaid_{random.randint(100_000,999_999)}'
  if 'doi' not in paper.keys():
    paper['doi'] = ''
  if 'type' not in paper.keys():
    paper['type'] = 'unknown'
  if 'title' not in paper.keys():
    paper['title'] = 'unknown'
  if 'publication_year' not in paper.keys():
    paper['publication_year'] = 0
  if 'cited_by_count' not in paper.keys():
      paper['cited_by_count'] = 0
  if 'abstract_inverted_index' not in paper.keys():
      paper['abstract_inverted_index'] = []
  if 'concepts' not in paper.keys():
      paper['concepts'] = []
  if 'primary_location' not in paper.keys():
      print(f"this paper does not have a primary location: {paper['id']}")
      paper['primary_location'] = {}

  return paper

# ----------------------------------------------------------------------------
def format_from_openalex_to_dimensions(papers):
  '''
  Format the list of papers downloaded with the Openalex API using `download_from_openalex()`
  to have the format of dimensions. So that we can use the rest of zenronbun.
  '''
  # Use Crossref for small datasets only. Too slow for large datasets.
  if len(papers) < 10000:
    infer = False # ðŸ”´ change to True when needed!
  else:
    infer = False

  # Init
  papers_dimensions = []

  for oap in papers:
    try:
      oap = sanitize_openalex_json(oap)
      authors, institutions, countries = format_authorship(oap['authorships'])
      dimensions_json = {
          'id':                         oap['id'],
          'doi':                        oap['doi'],
          'type':                       oap['type'].replace('journal-', ''),
          'title':                      oap['title'],
          'year':                       int(oap['publication_year']),
          'times_cited':                int(oap['cited_by_count']),
          'abstract':                   format_abstract(oap['abstract_inverted_index']),
          'concepts':                   format_concepts(oap['concepts']),
          'journal.title':              format_journal(oap['primary_location'], oap['doi'], infer = infer),
          'researchers':                authors,
          'research_org_names':         institutions,
          'research_org_country_names': countries,
          'reference_ids':              oap['referenced_works'],
          'is_oa':                      find_if_open_access(oap['primary_location']),
          'is_retracted':                oap['is_retracted']
      }
    except Exception as e:
      print(e)
      print(oap['doi'])
      print(f"https://api.openalex.org/works/{oap['doi']}")
      raise
    papers_dimensions.append(dimensions_json)
  return papers_dimensions

# ----------------------------------------------------------------------------
# NEW 20250416

# Query. Term search
KEYWORDS = '''
("artificial intelligence" OR AI OR "machine learning" OR "deep learning" OR "neural network" OR "neural networks" OR "natural language processing" OR "large language model" OR "large language models" OR LLM OR LLMs OR "generative AI" OR "artificial general intelligence" OR AGI OR "predictive analytics" OR "intelligent system" OR "intelligent systems" OR "big data" OR "data analytics" OR "data mining") AND ("eco-innovation" OR "eco innovation" OR ecoinnovation OR "environmental innovation" OR "green innovation" OR "sustainable innovation" OR "sustainability innovation" OR "sustainability-oriented innovation" OR "sustainability oriented innovation" OR "sustainability-driven innovation" OR "sustainability driven innovation" OR "sustainable technological innovation" OR "green technological innovation" OR "green technology innovation" OR "circular innovation" OR "low-carbon innovation" OR "low carbon innovation" OR "climate innovation" OR "clean technology" OR "clean technologies" OR cleantech OR "clean tech")
'''
#patent* AND ("artificial intelligence" OR "machine learning")
#@markdown The start/end year of publications used to extract patents
YEAR_START = 1900 #@param {type: "slider", min: 1950, max: 2025}
YEAR_END = 2026  #@param {type: "slider", min: 1950, max: 2025}

if YEAR_END < YEAR_START:
  YEAR_END = YEAR_START


############## DO NOT CHANGE!
# Check the publications available
formatted_query = create_query_string_for_openalex(KEYWORDS, YEAR_START, YEAR_END) #advanced=advanced
print('Click this link to verify the JSON data from openalex')
print(formatted_query)
print(' ')
response = requests.get(formatted_query)
print(f"Total articles for this query: {response.json()['meta']['count']}")

# ----------------------------------------------------------------------------
test = response.json()['results'][0]
test

# ----------------------------------------------------------------------------
# Download the data
papers = download_from_openalex(formatted_query)
len(papers)

# ----------------------------------------------------------------------------
# Convert to dimensions format
papers_dimensions = format_from_openalex_to_dimensions(papers)

# ----------------------------------------------------------------------------
# Convert records to dataframe
pubs = pd.DataFrame().from_dict(papers_dimensions)
print("Publications: ", len(pubs))
pubs.drop_duplicates(subset='id', inplace=True)
print("Unique Publications: ", len(pubs))

pubs.head(5)

# ----------------------------------------------------------------------------
print(pubs.title[0:10])

# ----------------------------------------------------------------------------
# # Identify the reviews
# reviews = pubs[pubs.title.str.contains("review|overview|landscape|survey|state-of-the-art|challenges and|and challenges|recommendations and|and recommendations", case=False)]
# print(len(reviews))
# reviews.head()

# ----------------------------------------------------------------------------
# Remove the reviews
# pubs = pubs[~pubs.title.str.contains("review|overview|landscape|survey|state-of-the-art|challenges and|and challenges|recommendations and|and recommendations", case=False)].reset_index(drop=True)
# print(len(pubs))
# pubs.head()

# ----------------------------------------------------------------------------
# Save serialized version of data from Dimensions
file = open(DATAFOLDER + '/raw_dataset_pickled_PART7', 'wb')
pickle.dump(pubs, file)
file.close()

# ----------------------------------------------------------------------------
pubs.to_csv(DATAFOLDER + '/openalex_pubs.csv', index=False)


