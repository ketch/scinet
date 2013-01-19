"""
Requires: bibtex.py
          bibliograph package
"""

bad_chars = ['\\','"']

def bibfile2dictlist(fname,do_postprocess=True,scopus=False,printupdates=False):
    """
    Takes a *.bib file name as input, and returns a list, with each
    element a dictionary corresponding to one of the BibTeX entries
    in the file.

    This should really be rewritten as a proper parser.
    Issues:
        - Chokes on blank lines in the middle of bibtex entries
    """

    from bibliograph.parsing.parsers.bibtex import BibtexParser
    import time

    bp=BibtexParser()
    f=file(fname)
    line=f.readline()

    biblist=[]

    entry=''
    while True:
        try: line=f.readline()
        except:
            bibrec=bp.parseEntry(entry)
            biblist.append(bibrec)
            if do_postprocess: biblist = postprocess(biblist)
            return biblist
        if line.startswith('@'):
            bibrec=bp.parseEntry(entry)
            if type(bibrec) is dict: biblist.append(bibrec)
            else: print 'Not a bibtex entry: '+entry
            entry=line
            if printupdates: print len(biblist)
            continue
        else:
            if scopus: #Scopus messes up the author format
                if line.strip().startswith('author='):
                    line=line.replace('a ',' ')
                    line=line.replace('b ',' ')
                    line=line.replace('c ',' ')
                    line=line.replace('d ',' ')
                    line=line.replace('e ',' ')
                    line=line.replace(' , ',' and ')
                    line=line.replace('., ','. and ')
            entry=entry+line
            if len(line)==0: 
                bibrec=bp.parseEntry(entry)
                if type(bibrec) is dict: biblist.append(bibrec)
                else: print 'Not a bibtex entry: '+entry
                if do_postprocess: biblist = postprocess(biblist)
                return biblist

    if do_postprocess: biblist = postprocess(biblist)
    return biblist


def postprocess(biblist):
    """
    Reformat the output of BibtexParser to be more helpful.
    """
    res=[]
    charstr='abcdefghijklmnopqrstuvwxyz1234567890 '
    for i,pub in enumerate(biblist):
        okay=True
        #Remove pubs that are just reports
        if pub['title'].find('Report')>-1: 
            okay=False
            print 'Report rejected: ',pub['title']
        #Remove non-English pubs:
        if pub.has_key('journal'): wherepub='journal'
        elif pub.has_key('booktitle'): wherepub='booktitle'
        elif pub.has_key('school'): wherepub='school'
        elif pub.has_key('institution'): wherepub='institution'
        else:
            print i, ' what is this one? ', pub['pid']
            print pub['reference_type']
            wherepub='title'
            okay=False
        capwords=[s.capitalize() for s in pub[wherepub].split()]
        engtest=' '.join(capwords)

        if engtest[0].lower() not in charstr:
            okay=False
            print 'Non-english pub rejected: ', pub['title']
            print pub[wherepub]
        if pub.has_key('publisher'):
            if pub['publisher'][0].lower() not in charstr:
                okay=False
                print 'Non-english pub rejected: ', pub['title']
                print 'Publisher: ',pub['publisher']
                print pub[wherepub]
        #reformat author set
        #Check if it is raw or already processed:
        if not pub.has_key('authors'):
            print 'Paper has no author'
            continue
        if type(pub['authors'][0]) is dict:
            authlist=[]
            for author in pub['authors']:
                firstname=author['firstname'].replace('.','').upper()
                # Remove strange characters that cause problems for pygraphviz:
                authname=firstname+' '+author['lastname'].capitalize()
                for char in bad_chars:
                    authname = authname.replace(char,'')
                authlist.append(authname)
            pub['authors']=authlist
        if ' others' in pub['authors']: pub['authors'].remove(' others')
        if okay: res.append(pub)
    return res


