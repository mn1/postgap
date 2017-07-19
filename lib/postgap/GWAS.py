#! /usr/bin/env python

"""

Copyright [1999-2016] EMBL-European Bioinformatics Institute

Licensed under the Apache License, Version 2.0 (the "License")
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

		 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

"""

	Please email comments or questions to the public Ensembl
	developers list at <http://lists.ensembl.org/mailman/listinfo/dev>.

	Questions may also be sent to the Ensembl help desk at
	<http://www.ensembl.org/Help/Contact>.

"""
import re
import requests
import json
import sys

import postgap.REST
import postgap.Globals
from postgap.DataModel import *
from postgap.Utils import *

import logging
import sys

#postgap.REST.DEBUG = False


class GWAS_source(object):
	def run(self, diseases, iris):
		"""

			Returns all GWAS SNPs associated to a disease in this source
			Args:
			* [ string ] (trait descriptions)
			* [ string ] (trait Ontology IRIs)
			Returntype: [ GWAS_Association ]

		"""
		assert False, "This stub should be defined"

class GWASCatalog(GWAS_source):
	display_name = 'GWAS Catalog'

	def run(self, diseases, iris):
		"""
			Returns all GWAS SNPs associated to a disease in GWAS Catalog
			Args:
			* [ string ] (trait descriptions)
			* [ string ] (trait Ontology IRIs)
			Returntype: [ GWAS_Association ]
		"""

		logger = logging.getLogger(__name__)

		if iris is not None and len(iris) > 0:
			res = concatenate(self.query(query) for query in iris)
		else:
			res = concatenate(self.query(query) for query in diseases)

		logger.debug("\tFound %i GWAS SNPs associated to diseases (%s) or EFO IDs (%s) in GWAS Catalog" % (len(res), ", ".join(diseases), ", ".join(iris)))

		return res

	def query(self, efo):
		logger = logging.getLogger(__name__)
		logger.info("Querying GWAS catalog for " + efo);
		
		# E.g.: http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/search/findByUri?uri=http://www.ebi.ac.uk/efo/EFO_0000400
		#
		# EFO_0000400 stands for diabetes mellitus
		#
		server = 'http://wwwdev.ebi.ac.uk'
		url = '/gwas/beta/rest/api/efoTraits/search/findByUri?uri=%s' % (efo)

		import postgap.REST
		hash = postgap.REST.get(server, url)

		'''
			hash looks like this:
			
			{
				"_embedded": {
					"efoTraits": [
						{
							"trait": "diabetes mellitus",
							"uri": "http://www.ebi.ac.uk/efo/EFO_0000400",
							"_links": {
								"self": {
									"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/71"
								},
								"efoTrait": {
									"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/71"
								},
								"studies": {
									"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/71/studies"
								},
								"associations": {
									"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/71/associations"
								}
							}
						}
					]
				},
				"_links": {
					"self": {
						"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/search/findByUri?uri=http://www.ebi.ac.uk/efo/EFO_0000400"
					}
				},
				"page": {
					"size": 20,
					"totalElements": 1,
					"totalPages": 1,
					"number": 0
				}
			}
		'''

		list_of_GWAS_Associations = []

		efoTraits = hash["_embedded"]["efoTraits"]
		
		for efoTraitHash in efoTraits:

			efoTraitLinks = efoTraitHash["_links"]
			efoTraitName  = efoTraitHash["trait"]

			logger.info("Querying Gwas rest server for SNPs associated with " + efoTraitName)

			association_rest_response = efoTraitLinks["associations"]
			association_url = association_rest_response["href"]
			try:
				# e.g.: http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/efoTraits/71/associations
				#
				association_response = postgap.REST.get(association_url, "")
			except:
				continue
			
			associations = association_response["_embedded"]["associations"]
			
			'''
				associations has this structure:
				
				[

					{
						"riskFrequency": "NR",
						"pvalueDescription": null,
						"pvalueMantissa": 2,
						"pvalueExponent": -8,
						"multiSnpHaplotype": false,
						"snpInteraction": false,
						"snpType": "known",
						"standardError": 0.0048,
						"range": "[NR]",
						"description": null,
						"orPerCopyNum": null,
						"betaNum": 0.0266,
						"betaUnit": "unit",
						"betaDirection": "increase",
						"lastMappingDate": "2016-12-24T07:36:49.000+0000",
						"lastUpdateDate": "2016-11-25T14:37:53.000+0000",
						"pvalue": 2.0E-8,
						"_links": {
							"self": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018"
							},
							"association": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018"
							},
							"study": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/study"
							},
							"snps": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/snps"
							},
							"loci": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/loci"
							},
							"efoTraits": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/efoTraits"
							},
							"genes": {
								"href": "http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/genes"
							}
						}
					},
				...
				]
			'''
			logger.info("Received " + str(len(associations)) + " associations with SNPs.")
			logger.info("Fetching SNPs and pvalues.")

			for current_association in associations:

				# e.g. snp_url can be: http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/associations/16513018/snps
				#
				snp_url = current_association["_links"]["snps"]["href"]
				snp_response = postgap.REST.get(snp_url, "")
				singleNucleotidePolymorphisms = snp_response["_embedded"]["singleNucleotidePolymorphisms"]

				if (len(singleNucleotidePolymorphisms) == 0):
					# sys.exit("Got no snp for a pvalue!")
					continue

				study_url = current_association["_links"]["study"]["href"]
				study_response = postgap.REST.get(study_url, "")
				pubmedId = study_response["pubmedId"]

				diseaseTrait_url = study_response["_links"]["diseaseTrait"]["href"]
				diseaseTrait_response = postgap.REST.get(diseaseTrait_url, "")
				diseaseTrait = diseaseTrait_response['trait']

				for current_snp in singleNucleotidePolymorphisms:
					if current_snp["rsId"] == '6':
						continue

					logger.debug("    received association with snp rsId: " + '{:12}'.format(current_snp["rsId"]) + " with a pvalue of " + str(current_association["pvalue"]))
					
					risk_alleles_href = current_snp["_links"]["riskAlleles"]["href"]
					import postgap.REST
					hash = postgap.REST.get(risk_alleles_href, ext="")
					riskAlleles = hash["_embedded"]["riskAlleles"]
					
					from methods.GWAS_Lead_Snp_Orientation                 \
					import                                                 \
					gwas_risk_alleles_present_in_reference,                \
					none_of_the_risk_alleles_is_a_substitution_exception,  \
					variant_mapping_is_ambiguous_exception,                \
					some_alleles_present_others_not_exception,             \
					no_dbsnp_accession_for_snp_exception
					
					try:
					
						if gwas_risk_alleles_present_in_reference(riskAlleles):
							risk_alleles_present_in_reference = True
							logging.info("Risk allele is present in reference");
						else:
							risk_alleles_present_in_reference = False
							logging.info("Risk allele is not present in reference");
					
					except none_of_the_risk_alleles_is_a_substitution_exception as e:
						logger.warning(str(e))
						logger.warning("Skipping this snp.")
						continue
					
					except variant_mapping_is_ambiguous_exception:
						logger.warning("The variant mapping is ambiguous.")
						logger.warning("Skipping this snp.")
						continue
					
					except some_alleles_present_others_not_exception as e:
						logger.warning(str(e));
						logger.warning("Skipping this snp.")
						continue
					
					except no_dbsnp_accession_for_snp_exception:
						logger.warning(str(e));
						logger.warning("Skipping this snp.")
						continue

					list_of_GWAS_Associations.append(
						GWAS_Association(
							disease = Disease(
								name = efoTraitName,
								efo  = efo
							),
							reported_trait = diseaseTrait,
							snp     = current_snp["rsId"],
							pvalue  = current_association["pvalue"],
							source  = 'GWAS Catalog',
							study   = 'PMID' + pubmedId,
							
							# For fetching additional information like risk allele later, if needed.
							# E.g.: http://wwwdev.ebi.ac.uk/gwas/beta/rest/api/singleNucleotidePolymorphisms/9765
							rest_hash = current_snp,
							risk_alleles_present_in_reference = risk_alleles_present_in_reference,
							
							odds_ratio                 = current_association["orPerCopyNum"],

							beta_coefficient           = current_association["betaNum"],
							beta_coefficient_unit      = current_association["betaUnit"],
							beta_coefficient_direction = current_association["betaDirection"],
						)
					)
		if len(list_of_GWAS_Associations) > 0:
			logger.info("Successfully fetched " +  str(len(list_of_GWAS_Associations)) + " SNPs and pvalues.")
		if len(list_of_GWAS_Associations) == 0:
			logger.info("Found no associated SNPs and pvalues.")
	
		return list_of_GWAS_Associations

class GRASP(GWAS_source):
	display_name = "GRASP"
	def run(self, diseases, iris):
		"""

			Returns all GWAS SNPs associated to a disease in GRASP
			Args:
			* [ string ] (trait descriptions)
			* [ string ] (trait Ontology IRIs)
			Returntype: [ GWAS_Association ]

		"""
		logger = logging.getLogger(__name__)
		
		file = open(postgap.Globals.DATABASES_DIR+"/GRASP.txt")
		res = [ self.get_association(line, diseases, iris) for line in file ]
		res = filter(lambda X: X is not None, res)

		logger.info("\tFound %i GWAS SNPs associated to diseases (%s) or EFO IDs (%s) in GRASP" % (len(res), ", ".join(diseases), ", ".join(iris)))

		return res

	def get_association(self, line, diseases, iris):
		'''

			GRASP file format:
			1. NHLBIkey
			2. HUPfield
			3. LastCurationDate
			4. CreationDate
			5. SNPid(dbSNP134)
			6. chr(hg19)
			7. pos(hg19)
			8. PMID
			9. SNPid(in paper)
			10. LocationWithinPaper
			11. Pvalue
			12. Phenotype
			13. PaperPhenotypeDescription
			14. PaperPhenotypeCategories
			15. DatePub
			16. InNHGRIcat(as of 3/31/12)
			17. Journal
			18. Title
			19. IncludesMale/Female Only Analyses
			20. Exclusively Male/Female
			21. Initial Sample Description
			22. Replication Sample Description
			23. Platform [SNPs passing QC]
			24. GWASancestryDescription
			25. TotalSamples(discovery+replication)
			26. TotalDiscoverySamples
			27. European Discovery
			28. African Discovery
			29. East Asian Discovery
			30. Indian/South Asian Discovery
			31. Hispanic Discovery
			32. Native Discovery
			33. Micronesian Discovery
			34. Arab/ME Discovery
			35. Mixed Discovery
			36. Unspecified Discovery
			37. Filipino Discovery
			38. Indonesian Discovery
			39. Total replication samples
			40. European Replication
			41. African Replication
			42. East Asian Replication
			43. Indian/South Asian Replication
			44. Hispanic Replication
			45. Native Replication
			46. Micronesian Replication
			47. Arab/ME Replication
			48. Mixed Replication
			49. Unspecified Replication
			50. Filipino Replication
			51. Indonesian Replication
			52. InGene
			53. NearestGene
			54. InLincRNA
			55. InMiRNA
			56. InMiRNABS
			57. dbSNPfxn
			58. dbSNPMAF
			59. dbSNPalleles/het/se
			60. dbSNPvalidation
			XX61. dbSNPClinStatus
			XX62. ORegAnno
			XX63. ConservPredTFBS
			XX64. HumanEnhancer
			XX65. RNAedit
			XX66. PolyPhen2
			XX67. SIFT
			XX68. LS-SNP
			XX69. UniProt
			XX70. EqtlMethMetabStudy
			71. EFO string

		'''
		items = line.rstrip().split('\t')
		for iri in items[70].split(','):
			if iri in iris:
				return GWAS_Association(
					pvalue = float(items[10]),
					snp = "rs" + items[4],
					disease = Disease(name = postgap.EFO.term(iri), efo = iri),
					reported_trait = items[12].decode('latin1'),
					source = self.display_name,
					study = items[7],
					rest_hash = None,
					risk_alleles_present_in_reference = None,
				)

		if items[12] in diseases:
			iri = items[70].split(',')[0]
			return GWAS_Association(
				pvalue = float(items[10]),
				snp = "rs" + items[4],
				disease = Disease(name = postgap.EFO.term(iri), efo = iri),
				reported_trait = items[12].decode('latin1'),
				source = self.display_name,
				study = items[7],
				rest_hash = None,
				risk_alleles_present_in_reference = None,
			)

		return None

class Phewas_Catalog(GWAS_source):
	display_name = "Phewas Catalog"
	logger = logging.getLogger(__name__)
	
	def run(self, diseases, iris):
		"""

			Returns all GWAS SNPs associated to a disease in PhewasCatalog
			Args:
			* [ string ] (trait descriptions)
			* [ string ] (trait Ontology IRIs)
			Returntype: [ GWAS_Association ]

		"""
		file = open(postgap.Globals.DATABASES_DIR+"/Phewas_Catalog.txt")
		res = [ self.get_association(line, diseases, iris) for line in file ]
		res = filter(lambda X: X is not None, res)

		self.logger.info("\tFound %i GWAS SNPs associated to diseases (%s) or EFO IDs (%s) in Phewas Catalog" % (len(res), ", ".join(diseases), ", ".join(iris)))

		return res

	def get_association(self, line, diseases, iris):
		'''

			Phewas Catalog format:
			1. chromosome
			2. snp
			3. phewas phenotype
			4. cases
			5. p-value
			6. odds-ratio
			7. gene_name
			8. phewas code
			9. gwas-associations
			10. [Inserte] EFO identifier (or N/A)

		'''
		items = line.rstrip().split('\t')
		for iri in items[9].split(','):
			if iri in iris:
				return GWAS_Association (
					pvalue = float(items[4]),
					snp = items[1],
					disease = Disease(name = postgap.EFO.term(iri), efo = iri), 
					reported_trait = items[2],
					source = self.display_name,
					study = "None",
					rest_hash = None
				)

		if items[2] in diseases: 
			iri = items[9].split(',')[0]
			return GWAS_Association (
				pvalue = float(items[4]),
				snp = items[1],
				disease = Disease(name = postgap.EFO.term(iri), efo = iri), 
				reported_trait = items[2],
				source = self.display_name,
				study = None,
				odds_ratio = None,
				beta_coefficient = None,
				beta_coefficient_unit = None,
				beta_coefficient_direction = None,
				rest_hash = None
			)

		return None

class GWAS_DB(GWAS_source):
	display_name = "GWAS DB"
	logger = logging.getLogger(__name__)
	
	def run(self, diseases, iris):
		"""

			Returns all GWAS SNPs associated to a disease in GWAS_DB
			Args:
			* [ string ] (trait descriptions)
			* [ string ] (trait Ontology IRIs)
			Returntype: [ GWAS_Association ]

		"""
		file = open(postgap.Globals.DATABASES_DIR+"/GWAS_DB.txt")
	
		res = [ self.get_association(line, diseases, iris) for line in file ]
		res = filter(lambda X: X is not None, res)

		self.logger.info("\tFound %i GWAS SNPs associated to diseases (%s) or EFO IDs (%s) in GWAS DB" % (len(res), ", ".join(diseases), ", ".join(iris)))

		return res

	def get_association(self, line, diseases, iris):
		'''

			GWAS DB data
			1. CHR
			2. POS
			3. SNPID
			4. P_VALUE
			5. PUBMED ID
			6. MESH_TERM
			7. EFO_ID

		'''
		items = line.rstrip().split('\t')
		for iri in items[6].split(','):
			if iri in iris:
				return GWAS_Association(
					pvalue = float(items[3]),
					snp = items[2],
					disease = Disease(name = postgap.EFO.term(iri), efo = iri),
					reported_trait = items[5].decode('latin1'),
					source = self.display_name,
					study = items[4],
					rest_hash = None,
					risk_alleles_present_in_reference = None,
				)

		if items[5] in diseases:
			iri = items[6].split(',')[0]
			return GWAS_Association(
				pvalue = float(items[3]),
				snp = items[2],
				disease = Disease(name = postgap.EFO.term(iri), efo = iri),
				reported_trait = items[5].decode('latin1'),
				source = self.display_name,
				study = items[4],
				rest_hash = None,
				risk_alleles_present_in_reference = None,
			)

		return None

sources = GWAS_source.__subclasses__()
