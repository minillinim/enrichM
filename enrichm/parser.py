#!/usr/bin/env python3
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

################################################################################
# Imports

from enrichm.databases import Databases

################################################################################
class Parser:
	'''
	A collection of functions to parse files in various formats.
	'''

	@staticmethod
	def parse_genome_and_annotation_file_lf(genome_and_annotation_file):
		genome_to_annotation_sets = dict()
		
		for line in open(genome_and_annotation_file):
			
			try:
				genome, annotation = line.strip().split("\t")
			
			except:
				raise Exception("Input genomes/annotation file error on %s" % line)
			
			if genome not in genome_to_annotation_sets:
				genome_to_annotation_sets[genome] = set()

			genome_to_annotation_sets[genome].add(annotation)
		
		return genome_to_annotation_sets
	
	@staticmethod
	def parse_genome_and_annotation_file_matrix(genome_and_annotation_matrix):
		genome_and_annotation_matrix_io = open(genome_and_annotation_matrix)
		headers=genome_and_annotation_matrix_io.readline().strip().split('\t')[1:]
		genome_to_annotation_sets = {genome_name:set() for genome_name in headers}

		for line in genome_and_annotation_matrix_io:
			sline = line.strip().split('\t')
			annotation, entries = sline[0], sline[1:]
			
			for genome_name, entry in zip(headers, entries):
			
				if float(entry) > 0:
					genome_to_annotation_sets[genome_name].add(annotation)

		return genome_to_annotation_sets
	
	@staticmethod
	def parse_taxonomy(taxonomy_path):
		
		output_taxonomy_dictionary = dict()

		for line in open(taxonomy_path):
			genome, taxonomy_string = line.strip().split('\t')
			output_taxonomy_dictionary[genome] = taxonomy_string.split(';')
			
		return output_taxonomy_dictionary
	
	@staticmethod
	def parse_simple_matrix(matrix, numeric = False):
		matrix_io = open(matrix)
		header_values = matrix_io.readline().strip().split('\t')[1:]
		output_dict = {header:{} for header in header_values}
		
		for line in matrix_io:
			sline = line.strip().split('\t')
			annot, content = sline[0], sline[1:]

			for key, value in zip(header_values, content):

				if numeric == True:
					value = float(value)
				output_dict[key][annot] = value

		return output_dict

	@staticmethod
	def parse_matrix(matrix_file_io, colnames):
		
		for line in matrix_file_io:
			sline = line.strip().split('\t')
			rowname, entries = sline[0], sline[1:]
		
			for colname, entry in zip(colnames, entries):
				yield colname, entry, rowname

	@staticmethod
	def parse_metadata_matrix(matrix_path):
		'''        
		Parameters
		----------
		matrix_path : String. Path to file containing a matrix of genome rownames.        
		'''

		matrix_file_io = open(matrix_path)
		cols_to_rows = dict()
		nr_values = set()
		attribute_dict = dict()

		for line in matrix_file_io:
			rowname, entry = line.strip().split('\t')   
			nr_values.add(entry)

			if entry in attribute_dict:
				attribute_dict[entry].add(rowname)
			else:
				attribute_dict[entry] = set([rowname])

			if rowname not in cols_to_rows:
				cols_to_rows[rowname] = set([entry])
			else:
				cols_to_rows[rowname].add(entry)
		
		return cols_to_rows, nr_values, attribute_dict

	@staticmethod
	def parse_single_column_text_file(text_file):
		entries = set()

		for entry in open(text_file):
			entry = entry.strip()
			entries.add(entry)

		return entries

	def filter_large_matrix(columns, matrix):
		'''
		description

		Inputs
		------

		Outputs
		-------

		'''
		logging.info('Parsing GTDB matrix')

		columns = list(columns)
		matrix_io = open(matrix)
		header = matrix_io.readline().strip().split('\t')

		indexes = list()
		include = list()
        
		for column in columns:
			
			if column in header:
				indexes.append(header.index(column))
				include.append(column)
				
		columns = include

		output_dict = {column:dict() for column in columns}
		
		for row in matrix_io:
			srow = row.strip().split()
			annotation = srow[0]

			for column, index in zip(columns, indexes):
				count = int(srow[index])

				if count > 0:
					output_dict[column][annotation] = int(srow[index])

		return output_dict, columns

	@staticmethod
	def parse_tpm_values(tpm_values):
		k2r = Databases().k2r

		output_dict = dict()
		annotation_types = set()
		genome_types = set()

		tpm_values_io = open(tpm_values, 'rb')
		tpm_values_io.readline()

		for line in tpm_values_io:
			gene, _, _, _, _, _, _, \
			_, _, _, tpm, \
			_, _,  annotation, sample = line.strip().split(b'\t')
			annotation_list = annotation.split(b',')
			tpm = float(tpm)
			genome = '_'.join(str(gene, "utf-8").split('_')[:2]) # temporary
			genome_types.add(genome)

			if sample not in output_dict:
				output_dict[sample] = dict()
			
			if genome not in output_dict[sample]:
				output_dict[sample][genome] = dict()

			for annotation_type in annotation_list:

				if str(annotation_type, "utf-8") in k2r:
					reactions = k2r[str(annotation_type, "utf-8")]

					for reaction in reactions:
						reaction = str.encode(reaction)

						if reaction not in output_dict[sample][genome]:
							output_dict[sample][genome][reaction] = 0.0
							annotation_types.add(reaction)
					
					output_dict[sample][genome][reaction] += tpm
												
		return output_dict, annotation_types, genome_types
