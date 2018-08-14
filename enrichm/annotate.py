#!/usr/bin/env python
###############################################################################
#                                                                             #
#    This program is free software: you can redistribute it and/or modify     #
#    it under the terms of the GNU General Public License as published by     #
#    the Free Software Foundation, either version 3 of the License, or        #
#    (at your option) any later version.                                      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program. If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

__author__      = "Joel Boyd"
__copyright__   = "Copyright 2017"
__credits__     = ["Joel Boyd"]
__license__     = "GPL3"
__version__     = "0.0.7"
__maintainer__  = "Joel Boyd"
__email__       = "joel.boyd near uq.net.au"
__status__      = "Development"
 
###############################################################################

# System imports
import logging
import subprocess
import os 
import pickle
import tempfile
import tempdir
import shutil

from databases import Databases
from matrix_generator import MatrixGenerator
from gff_generator import GffGenerator
from genome import Genome, AnnotationParser
from Bio import SeqIO

###############################################################################
################################ - Classes - ##################################

class Annotate:

    GENOME_BIN          = 'genome_bin'
    GENOME_PROTEINS     = 'genome_proteins'    
    GENOME_KO           = 'annotations_ko'
    GENOME_PFAM         = 'annotations_pfam'
    GENOME_TIGRFAM      = 'annotations_tigrfam'
    GENOME_HYPOTHETICAL = 'annotations_hypothetical'
    GENOME_GFF          = 'annotations_gff'
    GENOME_OBJ          = 'annotations_genomes'
    OUTPUT_KO           = 'ko_frequency_table.tsv'
    OUTPUT_PFAM         = 'pfam_frequency_table.tsv'
    OUTPUT_TIGRFAM      = 'tigrfam_frequency_table.tsv'
    OUTPUT_HYPOTHETICAL = 'hypothetical_frequency_table.tsv'
    OUTPUT_HYPOTHETICAL_ANNOTATIONS = 'hypothetical_annotations.tsv'

    GFF_SUFFIX          = '.gff'
    PROTEINS_SUFFIX     = '.faa'
    ANNOTATION_SUFFIX   = '.tsv'
    PICKLE_SUFFIX       = '.pickle'
    
    def __init__(self,
                 output_directory,
                 ko,
                 pfam,
                 tigrfam,
                 hypothetical,
                 evalue,
                 bit,
                 id,
                 aln_query,
                 aln_reference,
                 c,
                 threads,
                 parallel,
                 suffix,
                 light):

        # Define inputs and outputs
        self.output_directory = output_directory

        # Define type of annotation to be carried out
        self.ko               = ko 
        self.pfam             = pfam 
        self.tigrfam          = tigrfam 
        self.hypothetical     = hypothetical 
        
        # Cutoffs
        self.evalue           = evalue 
        self.bit              = bit 
        self.id               = id 
        self.aln_query        = aln_query
        self.aln_reference    = aln_reference
        self.c                = c

        # Parameters
        self.threads          = threads
        self.parallel         = parallel
        self.suffix           = suffix
        self.light            = light

        # Load databases
        self.databases        = Databases()

    def prep_genome(self, genome_file_list):
        '''
        Do any preparation specific to the genome annotation pipeline. 

        Inputs
        ------
        genome_file_list - List. list of strings, each a path to a file
        containing a genome 

        Outputs
        -------
        returns the directory with all genome ids sym-linked into it.
        '''
        # link all the genomes into one file    
        genome_directory=None
        if genome_file_list:
            genome_directory = os.path.join(self.output_directory, 
                                           self.GENOME_BIN)
            os.mkdir(os.path.join(self.output_directory, self.GENOME_BIN))
            for genome_path in genome_file_list:
                shutil.copy(os.path.join(os.getcwd(),
                                        genome_path), 
                           os.path.join(genome_directory, 
                                        os.path.basename(genome_path)
                                        )
                           )    
        return genome_directory


    def call_proteins(self, genome_directory):
        '''
        Use prodigal (https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-11-119)
        to call proteins within the genomes 
        
        Parameters
        ----------
        genome_directory  - string. Directory containing .fna files for each  
                            input genome

        Outputs
        -------
        returns the directory containing an .faa file for each input genomes
        '''   
        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_PROTEINS) 
        os.mkdir(output_directory_path)
        genome_list = list()
        genome_paths = list()

        for genome in os.listdir(genome_directory):
            if genome.endswith(self.suffix):
                genome_paths.append(os.path.splitext(genome)[0])
        logging.info("    - Calling proteins for %i genomes" % (len(genome_paths)))
        cmd = "ls %s/*%s | sed 's/%s//g' | grep -o '[^/]*$' | parallel -j %s prodigal -q -p meta -o /dev/null -a %s/{}%s -i %s/{}%s  > /dev/null 2>&1" \
                % (genome_directory,
                   self.suffix,
                   self.suffix,
                   self.parallel,
                   output_directory_path,
                   self.PROTEINS_SUFFIX,
                   genome_directory,
                   self.suffix)

        logging.debug(cmd)
        subprocess.call(cmd, shell = True)

        for genome_protein, genome_nucl in zip(os.listdir(output_directory_path), os.listdir(genome_directory)):
            output_genome_protein_path = os.path.join(output_directory_path, genome_protein)
            output_genome_nucl_path = os.path.join(genome_directory, genome_nucl)
            genome = Genome(self.light, output_genome_protein_path, output_genome_nucl_path)
            genome_list.append(genome)
        
        return genome_list
    
    def annotate_ko(self, genomes_list):
        '''
        Annotate the proteins encoded by each genome with KO ids using either BLAST or using HMM
        searches (no implemented yet).

        Parameters
        ----------        
        genome_faa_directory  - string. Directory containing .faa files for 
                                each input genome
        
        Outputs
        -------
        returns a directory containing the search results for each of the input population genomes, 
        and a frequency matrix contining with the KOs as rows, and the genomes as columns.
        '''        

        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_KO)
        os.mkdir(output_directory_path)
        for genome in genomes_list:
            output_annotation_path = os.path.join(output_directory_path, genome.name) + self.ANNOTATION_SUFFIX
            logging.info('    - BLASTing genome: %s' % (genome.name))
            self._diamond_search(genome.path, output_annotation_path, self.databases.KO_DB)
            genome.add(output_annotation_path, 
                         self.evalue, 
                         self.bit, 
                         self.aln_query, 
                         self.aln_reference,
                         AnnotationParser.KO)

    def _diamond_search(self, input_genome_path, output_path, database):
        '''
        Carry out a diamond blastp search. 

        Parameters
        ----------   
        input_genome_path     - string. Path to file containing .faa file for 
                                an input genome
        output_path           - string. Path to file to output results into    
        databases             - string. Path to HMM to use for searching         
        '''  
         
        cmd = 'diamond blastp --quiet --outfmt 6 --max-target-seqs 1 --query %s --out %s --db %s --threads %s ' \
                            % (input_genome_path, output_path, database, self.threads)
        if self.evalue:
            cmd += '--evalue %f ' % (self.evalue) 
        if self.bit:
            cmd += '--min-score %f ' % (self.bit)
        if self.id:
            cmd += '--id %f ' % (self.id)
        if self.aln_query:
            cmd += "--query-cover %f " % (self.aln_query * 100)
        if self.aln_reference:
            cmd += "--subject-cover %f " % (self.aln_reference * 100)

        logging.debug(cmd)
        subprocess.call(cmd, shell = True)

    def annotate_pfam(self, genomes_list):
        '''
        Annotate the proteins encoded by each genome with pfam ids using HMM searches.

        Parameters
        ----------        
        genomes_list  - list. list of Genome objects        

        '''    
        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_PFAM)
        os.mkdir(output_directory_path)
        genome_dict = {genome.name: genome for genome in genomes_list}
        self._hmm_search(genome_dict.keys(), output_directory_path, self.databases.PFAM_DB)

        for genome_annotation in os.listdir(output_directory_path):
            genome_id = os.path.splitext(genome_annotation)[0]
            genome = genome_dict[genome_id]
            output_annotation_path = os.path.join(output_directory_path, genome_annotation)

            genome.add(output_annotation_path, 
                         self.evalue, 
                         self.bit, 
                         self.aln_query, 
                         self.aln_reference,
                         AnnotationParser.PFAM)
    
    def annotate_tigrfam(self, genomes_list):
        '''
        Annotate the proteins encoded by each genome with tigrfam ids using HMM searches.

        Parameters
        ----------        
        genomes_list  - list. list of Genome objects        

        '''    
        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_TIGRFAM)
        os.mkdir(output_directory_path)     
        genome_dict = {genome.name: genome for genome in genomes_list}
        self._hmm_search(genome_dict.keys(), output_directory_path, self.databases.TIGRFAM_DB)

        for genome_annotation in os.listdir(output_directory_path):
            genome_id = os.path.splitext(genome_annotation)[0]
            genome = genome_dict[genome_id]
            output_annotation_path = os.path.join(output_directory_path, genome_annotation)
            genome.add(output_annotation_path, 
                         self.evalue, 
                         self.bit, 
                         self.aln_query, 
                         self.aln_reference,
                         AnnotationParser.TIGRFAM)

    def annotate_hypothetical(self, genomes_list):
        '''
        Sort proteins coded by each genome into homologous clusters.  
        
        Inputs
        ------
        genomes_list  - list. list of Genome objects        

        '''
        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_HYPOTHETICAL)
        os.mkdir(output_directory_path)      

        with tempfile.NamedTemporaryFile() as tmp_file:

            for genome in genomes_list:
                cmd = "sed \"s/>/>%s~/g\" %s >> %s" % (genome.name, genome.path, tmp_file.name)
                logging.debug(cmd)
                subprocess.call(cmd, shell = True)


            with tempdir.TempDir() as tmp_dir: 
                
                db_path = os.path.join(output_directory_path, "db")
                clu_path = os.path.join(output_directory_path, "clu")
                clu_tsv_path = os.path.join(output_directory_path, "hypothetical_clusters.tsv")

                logging.info('    - Generating MMSeqs2 database')
                cmd = 'mmseqs createdb %s %s -v 0 > /dev/null 2>&1' % (tmp_file.name, db_path)
                logging.debug(cmd)
                subprocess.call(cmd, shell = True)
                
                logging.info('    - Clustering genome proteins')
                cmd = 'mmseqs cluster %s %s %s --max-seqs 1000 --threads %s --min-seq-id %s -e %f -c %s > /dev/null 2>&1 ' \
                            % (db_path, clu_path, tmp_dir, self.threads, self.id, self.evalue, self.c)
                logging.debug(cmd)
                subprocess.call(cmd, shell = True)

                logging.info('    - Extracting clusters')
                cmd = 'mmseqs createtsv %s %s %s %s  > /dev/null 2>&1 ' % (db_path, db_path, clu_path, clu_tsv_path)
                logging.debug(cmd)
                subprocess.call(cmd, shell = True)
                
        cluster_ids = self.parse_cluster_results(clu_tsv_path, genomes_list, output_directory_path)

        return cluster_ids

    def parse_cluster_results(self, 
                              cluster_output_path,
                              genomes_list,
                              output_directory_path):
        '''
        Parse cluster output in tab format.
        
        Inputs
        ------
        from_cluster_results    - String. Path to mmseqs2 clustering output file
        
        Yields
        -------
        A cluster name, and a list of sequences in that cluster.
        
        '''
        logging.info('    - Parsing input cluster file: %s' % cluster_output_path)
        
        cluster_ids             = set()
        previous_cluster_name   = None
        counter                 = 0
        genome_dictionary       = {genome.name:genome for genome in genomes_list}

        with open(os.path.join(output_directory_path, self.OUTPUT_HYPOTHETICAL_ANNOTATIONS), 'w') as out_io:

            for line in open(cluster_output_path):
    
                cluster_id, member      = line.strip().split('\t')
                genome_id, sequence_id  = member.split('~')
                    
                if cluster_id == previous_cluster_name:
                    genome_dictionary[genome_id].add_cluster(sequence_id, "cluster_%i" % counter)
                else:
                    counter += 1
                    previous_cluster_name = cluster_id 
                    cluster_ids.add("cluster_%i" % counter)
                    genome_dictionary[genome_id].add_cluster(sequence_id, "cluster_%i" % counter)
                
                out_io.write('\t'.join([genome_id, sequence_id, "cluster_%i" % counter]) + '\n')
        import IPython ; IPython.embed()
        return cluster_ids

    def _hmm_search(self, genome_names, output_path, database):
        '''
        Carry out a hmmsearch. 

        Parameters
        ----------   
        input_genome_path     - string. Path to file containing .faa file for 
                                an input genome
        output_path           - string. Path to file to output results into   
        databases             - string. Path to HMM to use for searching          
        '''
        
        input_genome_path = os.path.join(self.output_directory, self.GENOME_PROTEINS)
        cmd = "ls %s | sed 's/%s//g' | parallel -j %s hmmsearch --cpu %s -o /dev/null --noali --domtblout %s/{}%s " \
                          % (input_genome_path, self.PROTEINS_SUFFIX, self.parallel, 
                             self.threads, output_path, self.ANNOTATION_SUFFIX)
        if self.evalue:
            cmd += '-E %f ' % (self.evalue) 
        if self.bit:
            cmd += '-T %f ' % (self.bit)    
        if self.id:
            logging.warning("--id flag not used for hmmsearch")

        cmd += "%s %s/{}.faa 2> /dev/null" % (database, input_genome_path)
        logging.debug(cmd)
        subprocess.call(cmd, shell = True)        

    def _parse_genome_proteins_directory(self, directory):
        '''
        Iterate through a directory and parse all .faa files it contains (assumed to be separate)
        genome bins

        Parameters 
        ----------
        directory   -   string. path to directory containing genome proteins.

        Outputs
        -------
        A list of Genome objects.
        '''
        genomes_list = []
        for genome_proteins_file in os.listdir(directory):
            if genome_proteins_file.endswith(self.suffix):
                genome = Genome(self.light, os.path.join(directory, genome_proteins_file))
                genomes_list.append(genome) 
        return genomes_list

    def _generate_gff_files(self, genomes_list):
        '''
        Write GFF files for each of the genome objects in genomes_list

        Parameters
        ----------
        genomes_list - List. List of Genome objects
        '''
        output_directory_path = os.path.join(self.output_directory, 
                                             self.GENOME_GFF)
        os.mkdir(output_directory_path)      
        for genome in genomes_list:
            logging.info('    - Generating .gff file for %s' % genome.name)
            gff_output = os.path.join(output_directory_path, genome.name + self.GFF_SUFFIX)
            gg = GffGenerator()
            gg.write(genome, gff_output)

    def _rename_fasta(self, genomes_list):
        '''
        Rename the called proteins with annotation ids.
        
        Parameters
        ----------
        genomes_list - List. List of Genome objects
        '''

        for genome in genomes_list:
            fd, fname = tempfile.mkstemp(suffix='.faa', text=True)
            with open(fname, 'w') as out_io:
                for sequence in SeqIO.parse(genome.path, 'fasta'):
                    annotations = ' '.join(genome.sequences[sequence.name].all_annotations())
                    out_io.write( ">%s %s\n" % (sequence.name, annotations) )
                    out_io.write( str(sequence.seq) + '\n' )
                
            shutil.move(fname, genome.path)

    def _pickle_objects(self, genomes_list):
        '''
        Store annotated genome objects as pickles.
        
        Parameters
        ----------
        genomes_list - List. List of Genome objects
        '''
        output_directory_path = os.path.join(self.output_directory,
                                             self.GENOME_OBJ)
        os.mkdir(output_directory_path)
        for genome in genomes_list:
            with open(os.path.join(output_directory_path, genome.name + self.PICKLE_SUFFIX), 'w') as output:
                pickle.dump(genome, output)

    def do(self, genome_directory, protein_directory, genome_files, protein_files):
        '''
        Run Annotate pipeline for enrichM

        Parameters
        ----------
        genome_directory    - String. Path to directory containing genomes
        protein_directory   - String. Path to directory containing proteins (.faa files) for genomes
        genome_files        - List. List of strings, each to a .fna genome file.
        protein_files       - List. List of strings, each to a .faa proteins file.
        '''

        logging.info("Running pipeline: annotate")
        logging.info("Setting up for genome annotation")

        if protein_directory:
            logging.info("Using provided proteins")
            genomes_list = self._parse_genome_proteins_directory(protein_directory)
        elif protein_files:
            logging.info("Using provided proteins")
            genomes_list = [Genome(self.light, protein_file) for protein_file in protein_files]
        elif genome_directory:
            logging.info("Calling proteins for annotation")
            genomes_list = self.call_proteins(genome_directory)
        elif genome_files:
            logging.info("Calling proteins for annotation")            
            genomes_list = self.call_proteins(self.prep_genome(genome_files))

        if len(genomes_list)==0:
            logging.error('There were no genomes found with the suffix %s within the provided directory' \
                                        %  (self.suffix))
        else:
            
            logging.info("Starting annotation:")

            if self.hypothetical:
                logging.info('    - Annotating genomes with hypothetical clusters')
                cluster_ids = self.annotate_hypothetical(genomes_list)
                
                logging.info('    - Generating hypotheticals frequency table') 
                mg = MatrixGenerator(MatrixGenerator.HYPOTHETICAL, cluster_ids)

                freq_table = os.path.join(self.output_directory, self.OUTPUT_HYPOTHETICAL)
                mg.write_matrix(genomes_list, freq_table)

            if self.ko:
                logging.info('    - Annotating genomes with ko ids')
                self.annotate_ko(genomes_list)

                logging.info('    - Generating ko frequency table')
                mg = MatrixGenerator(MatrixGenerator.KO)
                
                freq_table = os.path.join(self.output_directory, self.OUTPUT_KO)
                mg.write_matrix(genomes_list, freq_table)

            if self.pfam:
                logging.info('    - Annotating genomes with pfam ids')
                self.annotate_pfam(genomes_list)

                logging.info('    - Generating pfam frequency table')
                mg = MatrixGenerator(MatrixGenerator.PFAM)
                
                freq_table = os.path.join(self.output_directory, self.OUTPUT_PFAM)
                mg.write_matrix(genomes_list, freq_table)

            if self.tigrfam:
                logging.info('    - Annotating genomes with tigrfam ids')
                self.annotate_tigrfam(genomes_list)
                
                logging.info('    - Generating tigrfam frequency table')
                mg = MatrixGenerator(MatrixGenerator.TIGRFAM)
                
                freq_table = os.path.join(self.output_directory, self.OUTPUT_TIGRFAM)
                mg.write_matrix(genomes_list, freq_table)
            
            logging.info('Generating .gff files:')
            self._generate_gff_files(genomes_list)

            if not(protein_directory or protein_files):
                logging.info('Renaming protein headers')
                self._rename_fasta(genomes_list)
            
            if self.light:
                pass
            else:
                logging.info('Storing genome objects')
                self._pickle_objects(genomes_list)

            logging.info('Finished annotation')

