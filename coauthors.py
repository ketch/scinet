"""
Build and manipulate graphs of co-authors.

To remove degree-1 nodes:

	nn = []
	for node in G.nodes_iter():
    		if G.degree(node)<2:
        		nn.append(node)        		
	for node in nn:
	    GG.remove_node(node)

To remove nodes with only one paper:

	nn = []
	for node in GG.nodes_iter():
    		if sum([edge['weight'] for edge in GG[node].values()])<=1.:
        		nn.append(node)
        for node in nn:             
	    GG.remove_node(node)
"""


import networkx as nx

def coauthor_graph(author):
    author_initials=author.split()[0].upper()
    author_lastname=author.split()[-1].capitalize()

    #Get coauthors of principal author
    coauthors,num_coauthored_pubs=get_coauthors(author)
    coauthor_initials =[ca.split()[0].upper() for ca in coauthors]
    coauthor_lastnames=[ca.split()[-1].capitalize() for ca in coauthors]
    print coauthors
    coauthors=[coauthor_initials[j]+' '+coauthor_lastnames[j] for j in range(len(coauthor_initials))]

    G=nx.Graph()
    G.add_node(author)
    for j in range(len(coauthors)):
        G.add_node(coauthors[j])
        G.add_edge(author,coauthors[j],num_coauthored_pubs[j])
    
    #Get secondary edges
    for coauthor in coauthors:
        this_coauthor_initials=coauthor.split()[0]
        this_coauthor_lastname=coauthor.split()[-1]
        time.sleep(5) #Go slowly so we aren't flagged as a bot
        co_co_authors,num_cocoauthored_pubs=get_coauthors(coauthor)
        for j in range(len(co_co_authors)):
            cca=co_co_authors[j]
            nccpubs=num_cocoauthored_pubs[j]
            cca_initials=cca.split()[0].upper()
            cca_lastname=cca.split()[-1].capitalize()
            #Check whether it is the same guy
            if cca_lastname!=this_coauthor_lastname or cca_initials[0]!=this_coauthor_initials[0]:
                #Check if it is someone in the graph
                cca_name=find_name_match(cca,coauthor_lastnames,coauthor_initials)
                if cca_name!=-1:
                    print 'found ',nccpubs, ' joint publications of ',coauthor,' with ', cca_name
                    if not G.has_edge(coauthor,cca_name): G.add_edge(coauthor,cca_name,nccpubs)
                    else: G.add_edge(coauthor,cca_name,max(nccpubs,G.get_edge_data(coauthor,cca_name)))

    print G.edges(data=True)
    return G


def plot_ca_graph(G,nodescale=20,fontsize=10,labelthreshold=2,edgescale=4):
    """
    Plot graph of coauthorship.

    Author nodes are sized proportionally to the number of publications.
    Edges are sized proportionally to the number of coauthored publications.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    #pos=nx.spring_layout(G)
    #Graphviz gives a different layout but chokes on some unicode things
    #pos=nx.graphviz_layout(G,prog='twopi')
    #pos=nx.graphviz_layout(G,prog='fdp')
    #pos=nx.graphviz_layout(G,prog='circo')
    pos=nx.graphviz_layout(G,prog='sfdp')
    #pos=nx.graphviz_layout(G,prog='dot')
    nodelabel={}
    nodeweights=[]
    for nodename in G.nodes_iter():
        node=G[nodename]
        nodeweights.append(sum([float(d['weight']) for d in node.values()]))
        if nodeweights[-1]>=labelthreshold: 
            print unicode(str(nodename),'utf-8'), nodeweights[-1]
            nodelabel[nodename]=unicode(str(nodename),'utf-8')

    #I have no idea why I was doing this, but I'm leaving it here just in case
    #I later find that it was necessary.
    #for edge in G.edges(data=True):
    #    edge[2]['weight']=str(edge[2]['weight'])
    #edge_weights=[float(edge[2]['weight']) for edge in G.edges(data=True)]

    edge_weights=np.array([edge[2]['weight'] for edge in G.edges(data=True)])
    nodesize=nodescale*(1+10*np.log2(nodeweights))
    nx.draw_networkx_nodes(G,pos,node_size=nodesize,node_color='c')
    nx.draw_networkx_labels(G,pos,font_size=fontsize,labels=nodelabel,font_weight='bold')
    nx.draw_networkx_edges(G,pos,edgelist=G.edges(),edge_color='r',edge_cmap=plt.cm.Blues,width=edgescale*edge_weights)


def author_format(auth_str):
    """
    Converts an author name to the appropriate string format.
    It is assumed that the string begins with the first initial, possibly
    followed by middle initial, possibly with periods, and ends with
    the last name.
    """
    author={}
    #All but last part are initials:
    asp=auth_str.split()
    initials=''.join(asp[0:-1])
    #Remove periods, if present, and capitalize:
    first=initials.replace('.','').upper()
    #Last part is last name:
    last=asp[-1].capitalize()
    return first+' '+last


#Functions below here are deprecated!!!!!!!!!!!!!!!!!!!!!!

def get_coauthors(author):
    """
    Return a list of all coauthors of author, with the number
    of coauthored publications.
    Author is a dictionary containing keys
     firstname  (for now, this is just the first initial(s), with no periods)
     lastname   (just 1)
     middlename (just 1)
    """
    publications=get_publications(author,pubdb)

    coauthors=[]
    num_coauthored_pubs=[]
    for pub in publications:
        for pub_author in pub['authors']:
            pub_author['firstname']=pub_author['firstname'].replace('.','').upper()
            pubauthor=pub_author_initials+' '+pub_author_lastname
            #Check that the coauthor is not just the principal author
            if (pub_author['lastname']!=author['lastname'] or pub_author['firstname'][0]!=author['firstname'][0]):
                #Now check that it's not an alias of a coauthor already found
                pubauthor_name=find_name_match(pubauthor,coauthor_lastnames,coauthor_initials)
                if pubauthor_name!=-1:
                    num_coauthored_pubs[coauthors.index(pubauthor_name)]+=1
                else: 
                    coauthors.append(pubauthor)
                    coauthor_initials.append(pub_author_initials)
                    coauthor_lastnames.append(pub_author_lastname)
                    num_coauthored_pubs.append(1)

    return coauthors,num_coauthored_pubs

def find_name_match(name,lastnames_list,initials_list):
    initials=name.split()[0].upper()
    lastname=name.split()[-1].capitalize()
    
    ind=0
    while ind<len(lastnames_list):
        try: i=lastnames_list.index(lastname,ind)
        except: return -1 #Not in the list
        if initials[0]==initials_list[i][0]: 
            return initials_list[i]+' '+lastnames_list[i]
        else: ind=i+1  #Last name matches but first initial doesn't
    return -1


def trim_small_components(G,threshold=None):
    """Remove small components of G that are not connected to the rest."""
    import networkx
    sg = networkx.connected_component_subgraphs(G)
    if threshold is None:
        threshold = len(sg[0])/5
    return networkx.union_all([g for g in sg if len(g)>=threshold])
