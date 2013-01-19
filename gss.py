import urllib2
from time import sleep

SEARCH_HOST = "http://scholar.google.com"
SEARCH_BASE_URL = "/scholar"
#Fool GS to make it think I'm a browser
headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
urlopen=urllib2.urlopen
Request=urllib2.Request

def search_publications(author):
    """
    Return a dictionary of all publications of author.
    Author should be a dictionary.
    """
    publications=[]
    publications=GoogleScholarSearch(author,searchtype='author',limit=1000000)
    print len(publications), ' publications found for ', author
    return publications

def GoogleScholarSearch(terms, limit=1000, searchtype=None, start=0):
    """
    This function searches Google Scholar using the specified terms.
    It returns a list of dictionaries. Each
    dictionary contains the information related to the article.

    terms: List of search terms
    limit: Maximum number of results to be returned (default=10)

    TODO: Add screen-scrape for number of citations, others?
    """
    from cookielib import LWPCookieJar
    import os.path

    COOKIEFILE = "cookies.lwp"
    cj = LWPCookieJar()

    #Scholar only returns bibtex links if the cookie "CF=4" is set
    if os.path.isfile(COOKIEFILE):
        #We already have the necessary cookie(s) saved in a file
        cj.load(COOKIEFILE)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
    else:
        #We need to get the cookie
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
        prefurl=SEARCH_HOST+"/scholar_setprefs?inststart=0&hl=en&lang=all&instq=&inst=cat-oclc&num=%2&scis=yes&scisf=4&submit=Save+Preferences"
        print prefurl
        req=Request(prefurl,None,headers)
        handle=urlopen(req)
        handle.close()
        cj.save(COOKIEFILE) #Save the cookie for future
    
    results = []
    finished=False

    while not finished:
        print 'hello'
        url=set_search_url(terms,limit,start,searchtype)

        #Now perform the search
        req=Request(url,None,headers)
        try: handle=urlopen(req)
        except:
            print 'Search did not finish -- GScholar blocked you!'
            return results
        html=handle.read()
        handle.close()
                    
        #Extract bibtex info for 100 papers at a time:
        nrec,partresults,keepgoing=extract_all_bibtex(html,start,limit)
        results.extend(partresults)

        if keepgoing and start+nrec<limit: 
            start=start+nrec
            print 'sleeping for 5...'
            sleep(30) #Go slowly so we aren't flagged as a bot
        else: finished=True

    print 'Postprocessing...'
    results=postprocess(results)
    return results


def extract_all_bibtex(html,start,limit):
    """
    Look up Bibtex links to obtain the publication information
    """
    from BeautifulSoup import BeautifulSoup
    from bibliograph.parsing.parsers.bibtex import BibtexParser

    bp=BibtexParser()
    html = html.decode('ascii', 'ignore')
    soup = BeautifulSoup(html)
    results=[]
    for irec, record in enumerate(soup('div',attrs={'class':'gs_ri'})):
        print start+irec
        #Skip records that are just citations, as they are often erroneous
        if str(record.contents[0]).find('CITATION')>-1: continue
        #If there's not BibTeX link, we're at the end:
        if str(record.contents[-1]).find('Import')==-1: break

        #if irec==limit-1: #The last entry is special
        #Bibtex links are tagged gs_fl
        links=record.find('div',{'class':'gs_fl'}) 
        biblink=[link for link in links('a') if 'bib?' in str(link)]
        biblink=biblink[0]
        #else:
        #    biblink=record('a')[-1]

        url_end=str(biblink.attrs[0][1])
        url = SEARCH_HOST+url_end
        print url
        req=Request(url,None,headers)
        try:
            handle=urlopen(req)
        except:
            print 'Search did not finish -- GScholar blocked you!'
            print 'restart at ', start+irec
            return irec,results,False
 
        bibtex_entry=handle.read()
        handle.close()

        bibrec=bp.parseEntry(bibtex_entry)
        try:
            print bibrec['pid']
        except:
            print 'something weird happened!!!!'
            return irec,results,True
        #Try to ignore junk entries
        if bibrec.has_key('publication_year'):
            if bibrec['publication_year'] is not '':
                results.append(bibrec)
                print 'accepted'
            else: print 'rejected'

        sleep(30) #Go slowly so we aren't flagged as a bot

    nrec=len(soup('p'))-2
    if nrec==limit: return nrec, results, True
    else: return nrec, results, False

#def get_cite_link:
#        t=terms.split()
#        params = urlencode({'q': '+'.join(terms)})
#        url = SEARCH_HOST+SEARCH_BASE_URL+"?"+params

def set_search_url(terms,limit,start,searchtype):
    """
    Generates the URL for the search
    Possible search types are:
        Default - Title words
        'author' - Author
        'cites' - get all papers citing first hit
    """
    from urllib import urlencode

    lim = min(limit-start,100)  #GScholar will only give 100 results at a time

    #Title keyword searches:
    if searchtype==None: 
        params = urlencode(
            {'q': "allintitle:"+'+'.join(terms), 'num': lim, 'start': start})

    #Author searches:
    #Format is "author:David-Ketcheson" or "author:DI-Ketcheson"?
    elif searchtype=='author': 
        names=terms.split()
        params = urlencode(
            {'q': "author:"+names[0]+"-"+names[1], 'num': lim, 'start': start})

    elif searchtype=='cites':
        url = SEARCH_HOST+SEARCH_BASE_URL+"?"+terms

    url = SEARCH_HOST+SEARCH_BASE_URL+"?"+params
    print url
    return url


def postprocess(results):
    """
    Reformat the output of BibtexParser to be more helpful.
    """
    res=[]
    charstr='abcdefghijklmnopqrstuvwxyz1234567890 '
    for i,paper in enumerate(results):
        print i
        okay=True
        #Remove papers that are just reports
        if paper['title'].find('Report')>-1: 
            okay=False
            print 'Report rejected: ',paper['title']
        #Remove non-English papers:
        if paper.has_key('journal'): wherepub='journal'
        elif paper.has_key('booktitle'): wherepub='booktitle'
        elif paper.has_key('school'): wherepub='school'
        elif paper.has_key('institution'): wherepub='institution'
        else:
            print i, ' what is this one?'
            print paper['reference_type']
            print paper['title']
            wherepub='title'
            okay=False
        capwords=[s.capitalize() for s in paper[wherepub].split()]
        engtest=' '.join(capwords)

        if engtest[0].lower() not in charstr:
            okay=False
            print 'Non-english paper rejected: ', paper['title']
            print paper[wherepub]
        if paper.has_key('publisher'):
            if paper['publisher'][0].lower() not in charstr:
                okay=False
                print 'Non-english paper rejected: ', paper['title']
                print 'Publisher: ',paper['publisher']
                print paper[wherepub]
        #reformat author set
        #Check if it is raw or already processed:
        if not paper.has_key('authors'):
            print 'Paper has no author'
            continue
        if type(paper['authors'][0]) is dict:
            authlist=[]
            for author in paper['authors']:
                firstname=author['firstname'].replace('.','').upper()
                authname=firstname+' '+author['lastname'].capitalize()
                authlist.append(authname)
            paper['authors']=authlist
        if ' others' in paper['authors']: paper['authors'].remove(' others')
        if okay: res.append(paper)
    return res



if __name__ == '__main__':
    pubs = GoogleScholarSearch(["breast cancer", "gene"], 2)
    for pub in pubs:
        #print pub['Title']
        #print pub['Authors']
        #print pub['JournalYear']
        #print pub['Terms']
        #print "======================================"
        print pubs.prettify()



#OLD SCREEN-SCRAPING CODE
#        #The authors are listed in a span tag with class=gs_a
#        allauthorPart = record.fetch('span', {'class': 'gs_a'})
#        authorPart=None
#        ii=-1
#        #Get the right one of these tags
#        while authorPart==None:
#            ii+=1
#            if str(allauthorPart[ii]).find('&#x25ba')==-1:
#                authorPart=allauthorPart[ii]
#        #Format is (authors) - (Journal)
#        authors=str(authorPart).split('-')[0]
#        #Authors separated by commas
#        authors=authors.split(',') 
#        authors[0]=authors[0].replace('<span class="gs_a">','')
#        for i in range(len(authors)): 
#            authors[i]=authors[i].strip()
#            authors[i]=authors[i].replace('<b>','')
#            authors[i]=authors[i].replace('</b>','')
#            authors[i]=authors[i].replace('</span>','')
#
#        while '' in authors: 
#            authors.remove('')
#            print authors
#            print authorPart
#

#            pubURL = record.a['href']
#            # Clean up the URL, make sure it does not contain '\' but '/' instead
#            pubURL = pubURL.replace('\\', '/')
#
#            pubTitle = ""
#    
#            for part in record.a.contents:
#                pubTitle += str(part)
#            
#            #if pubTitle == "":
##            #    print '================================'
#            #    print record
#            #    print '================================'
#            #    print record.a
#            #    print '================================'
#            #    print record.a['href']
#            #    match1 = re.findall('<b>\[CITATION\]<\/b><\/font>(.*)- <a',str(record))
#            #    match2 = re.split('- <a',match1[citations])
#            #    pubTitle = re.sub('<\/?(\S)+>',"",match2[0])
#            #    citations = citations + 1
#           

##                possible_citations=record.fetch('a', {'class': 'fl'})
##                jj=-1
##                citation_link_found=False
##                while citation_link_found==False:
#                
#            
#            #This next section doesn't work and needs to be fixed:
#            authorPart = record.first('font', {'color': 'green'}).string
#            if str(authorPart)=='Null':     
#                authorPart = ''
#                # Sometimes even BeautifulSoup can fail, fall back to regex
#                m = re.findall('<font color="green">(.*)</font>', str(record))
#                if len(m)>0: authorPart = m[0]
#            num = authorPart.count(" - ")
#            # Assume that the fields are delimited by ' - ', the first entry will be the
#            # list of authors, the last entry is the journal URL, anything in between
#            # should be the journal year
#            idx_start = authorPart.find(' - ')
#            idx_end = authorPart.rfind(' - ')
#            pubAuthors = authors
#            pubJournalYear = authorPart[idx_start + 3:idx_end]
#            pubJournalURL = authorPart[idx_end + 3:]
#            # If (only one ' - ' is found) and (the end bit contains '\d\d\d\d')
#            # then the last bit is journal year instead of journal URL
#            if pubJournalYear=='' and re.search('\d\d\d\d', pubJournalURL)!=None:
#                pubJournalYear = pubJournalURL
#                pubJournalURL = ''
#            #End Broken Section (?)
#           
#            # This can potentially fail if all of the abstract can be contained in the space
#            # provided such that no '...' is found
#            delimiter = soup.firstText("...").parent
#            pubAbstract = ""
#            while str(delimiter)!='Null' and (str(delimiter)!='<b>...</b>' or pubAbstract==""):
#                pubAbstract += str(delimiter)
#                delimiter = delimiter.nextSibling
#            pubAbstract += '<b>...</b>'
#
#            match = re.search("Cited by ([^<]*)", str(record))
#            pubCitation = ''
#            if match != None:
#                pubCitation = match.group(1)
#            results.append({
#                "URL": pubURL,
#                "Title": pubTitle,
#                "Authors": pubAuthors,
#                "JournalYear": pubJournalYear,
#                "JournalURL": pubJournalURL,
#                "Abstract": pubAbstract,
#                "NumCited": pubCitation,
#                "Terms": terms
#                })
#        return irec+1,results

