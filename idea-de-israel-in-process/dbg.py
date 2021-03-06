# code taken from https://raw.githubusercontent.com/pmelsted/dbg/master/dbg.py
# import multiprocessing as mp
import argparse
import collections
from Bio import Seq, SeqIO, SeqRecord
import gfapy

#  Create reverse complement

def twin(km):
    return Seq.reverse_complement(km)

# Chunk reads into k sized chunks 
def kmers(seq,k):
    all_kmers = []
    for i in range(len(seq)+1-k):
         all_kmers.append(seq[i:i+k])
    return all_kmers

# Move sequence analysis one nucleotide forward  
def fw(km):
    for x in 'ACGT':
        yield km[1:]+x
# Move sequence analysis one nucleotide backward
def bw(km):
    for x in 'ACGT':
        yield x + km[:-1]

# count kmers and build dictionary with counts
# use limit as cut off of very down regulated seq 
def build(fn,k=31,limit=1):
    d = collections.defaultdict(int)

    # For each filename in input parse fast.q file 
    for f in fn:
        reads = SeqIO.parse(f,'fastq')
        # Extract reads 
        for read in reads:
            seq_s = str(read.seq)
            seq_l = seq_s.split('N')
            # 
            for seq in seq_l:
                for km in kmers(seq,k):
                    try:
                        d[km] +=1
                    except:
                        d[km] = 1
                seq = twin(seq)
                for km in kmers(seq,k):
                    try:
                        d[km] +=1
                    except:
                        d[km] = 1

 # Remove k-mer elements of dict that
    d1 = [x for x in d if d[x] <= limit]
    for x in d1:
        del d[x]

    return d

def merge_dicts(d1,d2):
    merge = {}
    for i in d1.keys():
        merge[i] = (d1[i], d2[i])
    for i in d2.keys():
        merge[i] = (d1[i], d2[i])
    return merge

# 
def contig_to_string(c):
    return c[0] + ''.join(x[-1] for x in c[1:])


# we will work here today 
def get_contig(d,km):
    c_fw = get_contig_forward(d,km)
    
    c_bw = get_contig_forward(d,twin(km))

    if km in fw(c_fw[-1]):
        c = c_fw
    else:
        c = [twin(x) for x in c_bw[-1:0:-1]] + c_fw
    return contig_to_string(c),c
        
# And here
def get_contig_forward(d,km):
    c_fw = [km]
    
    while True:
        if sum(x in d for x in fw(c_fw[-1])) != 1:
            break
        
        cand = [x for x in fw(c_fw[-1]) if x in d][0]
        if cand == km or cand == twin(km):
            break # break out of cycles or mobius contigs
        if cand == twin(c_fw[-1]):
            break # break out of hairpins
        
        if sum(x in d for x in bw(cand)) != 1:
            break

        c_fw.append(cand)

    return c_fw

def all_contigs(d,k):
    done = set()
    r = []
    for x in d:
        if x not in done:
            s,c = get_contig(d,x)
            for y in c:
                done.add(y)
                done.add(twin(y))
            r.append(s)
    
    G = {}
    heads = {}
    tails = {}
    for i,x in enumerate(r):
        G[i] = ([],[])
        heads[x[:k]] = (i,'+')
        tails[twin(x[-k:])] = (i,'-')
    
    for i in G:
        x = r[i]
        for y in fw(x[-k:]):
            if y in heads:
                G[i][0].append(heads[y])
            if y in tails:
                G[i][0].append(tails[y])
        for z in fw(twin(x[:k])):
            if z in heads:
                G[i][1].append(heads[z])
            if z in tails:
                G[i][1].append(tails[z])

    return G,r

# def kmer_count(cs,d, k, id):
#     global g
#     for x in range(0,len(cs)+1-k):              #  to get all subsegmet, holds the all the kmers
#         key = cs[x:x+k]
        
#         g.add_line("S\t%s:%s:(A:%s,B:%s)\t%s"%(id,x,d[key][0],d[key][1],key))     # To get kmer for organism A      

# Write to line
def write_GFA2(G,cs,k,d): 
    global args
    # for key, count in d.items():
    #     g.add_line("#\t%s\t%s"%(key,count))
    if args.output:                                             # If the output file name is given use it
        filename = args.output
    else:                                                       # else use standard one
        filename = "output.gfa"
    with open(filename,'w') as file:     
        file.write("H\tVN:Z:1.0\n")                           # Get the header with the GFA version to the GFA
        for i,x in enumerate(cs):                           # Get the one contig and a number id for the contig
            file.write("S\t%d\t%s\n"%(i, x))                 # Write the segment(contig) <segment>  <- S <sid:id> <slen:int> <sequence> <tag>*

        for i in G:                                             # Get the links to the gfa
            for j,o in G[i][0]:
                file.write("L\t%d\t+\t%d\t%s\t%dM\n"%(i,j,o,k-1))
            for j,o in G[i][1]:
                file.write("L\t%d\t-\t%d\t%s\t%dM\n"%(i,j,o,k-1))
        
        for key, count in d.items():
            file.write("#\t%s\t%s\n"%(key,count))



def main():
    global args

    dA = build(args.A, args.k, 1)
    
    dB = build(args.B, args.k, 1)
    d = merge_dicts(dA, dB)

    G,cs = all_contigs(d,args.k)
    write_GFA2(G,cs,args.k,d)


parser = argparse.ArgumentParser(description="Creates a GFA file with one or two organisms given a kmer size")
parser.add_argument("-k", type=int, required=True, help="the kmer size")
parser.add_argument("-A", nargs='+', required=True, help="Organism_A_files")
parser.add_argument("-B", nargs='+', required=True, help="Organism_B_files")
parser.add_argument("-output",required=False,help="Output GFA file name")
args = parser.parse_args()
# g = gfapy.Gfa()

# To add more organisms add this parser.add_argument("-B", nargs='+', required=True, help="Organism_B_files")
# change the name and do another call to build and do multiple merge_dicts calls


if __name__ == "__main__":
    main()