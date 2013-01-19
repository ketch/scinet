"""
Class for operating on bibliograhpic databases.  Use bibfile2dictlist() on
a bibtex file to get a list appropriate for conversion to a PublicationDatabase.

Examples:

Create a coauthor graph from an existing bibtex file:

    >>> import bibdig
    >>> publist=bibdig.bibfile2dictlist('ssp_search.bib')
    >>> import publication_database
    >>> pubdb=publication_database.PublicationDatabase(publist)
    >>> G=pubdb.author_graph()
    >>> import coauthors
    >>> coauthors.plot_ca_graph(G)

To generate the graph in Gephi, do:

    >>> import networkx
    >>> networkx.write_graphml(G,'ca_graph.graphml')
	
then load the graphml file in Gephi and to make things look nice you 
might follow the instructions at

https://github.com/stared/tag-graph-map-of-stackexchange

To extract just the largest connected component of the graph:

    >>> G = networkx.connected_component_subgraphs(G)[0]

"""
bad_chars = ['\\','"']
def load(fname):
    import pickle
    f=file(fname)
    return PublicationDatabase(pickle.load(f))

class PublicationDatabase(list):

    def __init__(self,publist):
        list.__init__(self,publist)

    def save(self,fname):
        import pickle
        f=file(fname,'w')
        pickle.dump(self,f)

    def merge(self,pubdb2):
        """
        Combine two publication databases by taking their union
        """
        pids=[pub['pid'] for pub in self]
        newpubs=[pub for pub in pubdb2 if pub['pid'] not in pids]
        self.extend(newpubs)

    def author_pubs(self,author):
        " Return all publications of author "
        publist = [pub for pub in self if author in pub['authors']]
        return publist

    def journal_pubs(self,journal):
        " Return all publications in one journal "
        journalpubs = [pub for pub in self if pub.has_key('journal')]
        publist = [pub for pub in journalpubs if pub['journal']==journal]
        return publist

    def npubs_by_journal(self):
        """ 
        Return a list of all journals in the database, with the
        number of publications appearing in each 
        """
        from  operator import itemgetter

        jpubs = [pub['journal'] for pub in self if pub.has_key('journal')]
        distinct=list(set(jpubs)) #Distinct journal names
        num_art = [jpubs.count(journal) for journal in distinct]
        z=zip(distinct,num_art)
        z.sort(key=itemgetter(1),reverse=False)
        return z

    def npubs_by_author(self):
        """ 
        Return a list containing a triple for each author in the database:

        (author name, number of publication, weighted number of publications)
        """
        from  operator import itemgetter

        authors=[]
        npubs=[]
        wpubs=[]
        for pub in self:
            num_authors=len(pub['authors'])
            for author in pub['authors']:
                if author not in authors:
                    authors.append(author)
                    npubs.append(1)
                    wpubs.append(1./num_authors)
                else:
                    ai=authors.index(author)
                    npubs[ai]+=1
                    wpubs[ai]+=1./num_authors
        z=zip(authors,npubs,wpubs)
        z.sort(key=itemgetter(1),reverse=False)
        return z


    def coauthors(self,author):
        """
        Return a list of all coauthors of author, with the number
        of coauthored publications.
        """
        from  operator import itemgetter

        pubs=self.author_pubs(author)
        #Get the set of unique coauthors
        coauthors=[]
        for pub in pubs:
            for pub_author in pub['authors']:
                if pub_author != author:
                    coauthors.append(pub_author)
        coauthors= list(set(coauthors))

        num_coauthored_pubs=[len(self.author_pubs(coauthor)) for coauthor in coauthors]

        #Now sort the list by the number of coauthored publications
        ca=zip(coauthors, num_coauthored_pubs)
        ca.sort(key=itemgetter(1),reverse=True)
        return ca


    def coauthor_graph(self,author):
        import networkx as nx
        #Get coauthors of principal author
        coauthors_and_num_pubs=self.coauthors(author)

        G=nx.Graph()
        G.add_node(author)

        for coauthor,num_coauthored_pubs in coauthors_and_num_pubs:
            G.add_node(coauthor)
            G.add_edge(author,coauthor,weight=num_coauthored_pubs)
        
        coauths=[ca for ca,np in coauthors_and_num_pubs]
        print coauths
        #Get secondary edges
        for coauthor,num_coauthored_pubs in coauthors_and_num_pubs:
            co_co_authors_and_num_cocoauthored_pubs=self.coauthors(coauthor)
            #Rewrite from here down..........................
            for cca,num_cocoauthored_pubs in co_co_authors_and_num_cocoauthored_pubs:
                #Check if it is someone (besides the principal) in the graph
                if cca in coauths:
                    if not G.has_edge(coauthor,cca): G.add_edge(coauthor,cca,weight=num_cocoauthored_pubs)
        return G


    def author_graph(self):
        """
        Construct the full graph of all coauthorships in the database.

        Each node is a 2-tuple consisting of a string and an int: 
        (author name, number of publications)
        """
        
        import networkx as nx

        G=nx.Graph()

        # Set up nodes
        npa = self.npubs_by_author()
        auths = [a[0] for a in npa]
        npubs = [a[1] for a in npa]
        for auth, npub in zip(auths,npubs):
            #G.add_node((auth,npub))
            pass

        for pub in self:
            #This is the only way I could figure to get everything into unicode so
            #that pygraphviz is happy with it.
            pub['authors']=[unicode(auth,'utf-8') for auth in pub['authors']]
            pub['authors']=[auth.encode('ascii','replace') for auth in pub['authors']]
            # Still have to delete some characters:
            for char in bad_chars:
                pub['authors']=[auth.replace(char,'') for auth in pub['authors']]
            for auth in pub['authors']:
                if not G.has_node(auth):
                    G.add_node(auth)
            
        for pub in self:
            num_authors=len(pub['authors'])
            for i,author in enumerate(pub['authors']):
                for author2 in pub['authors'][i+1:]:
                    if G.has_edge(author,author2):
                        G[author][author2]['weight']+=1./(num_authors-1)
                    else:
                        G.add_edge(author,author2,weight=1./(num_authors-1))
        return G

    def list_lastname_matches(self, lastname, inclusive=True):
        """Return all authors with a given last name."""
        matches = []
        for pub in self:
            for author in pub['authors']:
                if not inclusive:
                    if author.split()[-1]==lastname:
                        if author not in matches:
                            matches.append(author)
                else:
                    if lastname in author.split()[-1]:
                        if author not in matches:
                            matches.append(author)
        return matches

    def remove_author_pubs(self, author):
        n = 0
        for pub in self:
            if author in pub['authors']:
                self.remove(pub)
                n += 1
        print n, ' publications removed'
