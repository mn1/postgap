# functions for one-dimensional and two-dimensional fine-mapping
# shotgun stochastic search
# 11 april 2017


import numpy
import math
import scipy
import scipy.stats
import itertools as it
import operator
import random
import sklearn
from scipy.stats import norm
from sklearn import preprocessing
from collections import namedtuple

OneDConfigurationSample_prototype = namedtuple(
	'OneDConfigurationSample', 
	[
		'configurations',
		'posterior',
		'log_BF',
		'configuration_size',
		'log_prior',
		'labels',
		'sample_label'
	]
)
OneDConfigurationSample_prototype.__new__.__defaults__ = (
	None,
	None,
	None,
	None,
	None,
	None,
	"Unnamed sample",
)

#import collections
finemap_summary_prototype = namedtuple(
	'finemap_summary_prototype', [
		'labels', 
		'prior',
		'posterior',
		'log_BF',
		'BF',
	]
)

class TranslationIndexException(Exception):
	pass

class OneDConfigurationSample(OneDConfigurationSample_prototype):
	'''
		Stores finemapping data on a set of configurations:
		configurations: dict(tuple => int); assigns to each configuration (tuple of indices) an index into the vectors below
		posterior: numpy.array (1D)
		log_BF: numpy.array (1D)
		log_prior: numpy.array (1D)
		configuration_size: numpy.array (1D), number of SNPs in the corresponding vector
	'''
	def __str__(self):
		return self.finemap_object_to_english()

	def finemap_object_to_english(self, max_show_at_top = 5, max_show_at_end = 2):
		
		finemap_summary_list = self.compute_finemap_summaries()
		
		total_configurations = len(finemap_summary_list)
			
		finemap_summary_list_sorted = sorted(
			finemap_summary_list, 
			cmp = lambda x,y: cmp(x.BF, y.BF),
			reverse = True
		)
		
		num_show_at_top = min(total_configurations, max_show_at_top)
		num_show_at_end = min(total_configurations, max_show_at_end)
		
		indentation = "    "
		
		summary_lines = [ "A total of %i configurations have been investigated in %s:" % (total_configurations, self.sample_label) ]
		
		for index in range(num_show_at_top):
			summary_lines.append(indentation + "- " + self.finemap_summary_object_to_english(finemap_summary_list_sorted[index]))

		if num_show_at_top<total_configurations:

			summary_lines.append(indentation +  "...")

			for index in range(total_configurations-num_show_at_end, total_configurations):
				summary_lines.append(indentation + "- " + self.finemap_summary_object_to_english(finemap_summary_list_sorted[index]))

		return "\n".join(summary_lines)

	def finemap_summary_object_to_english(self, finemap_summary):
		
		snps_stringified = "(" + ', '.join(finemap_summary.labels) + ")"
		
		prior     = finemap_summary.prior
		posterior = finemap_summary.posterior
		BF        = finemap_summary.BF
		
		sentence = "The snp configuration {} has a prior probability of {:1.0%}. The posterior probability is {:.2e}. The Bayes factor is: {:.2e}".format(
				snps_stringified, prior, posterior, BF
			)

		return sentence

	def lookup_labels_for_snp_configuration(self, configuration):
		
		labels = []
		
		for position, configuration_index in enumerate(configuration):
			labels.append(self.labels[configuration_index])
		
		return labels

	def compute_finemap_summaries(self):
		
		configurations     = self.configurations
		posterior          = self.posterior
		log_BF             = self.log_BF
		configuration_size = self.configuration_size
		log_prior          = self.log_prior
		labels             = self.labels
		
		finemap_summary_list = []
		
		for current_configuration in configurations.keys():
			
			index_of_current_configuration = configurations[current_configuration]
			
			current_labels = self.lookup_labels_for_snp_configuration(current_configuration)
			
			import math
			current_finemap_summary = finemap_summary_prototype(
				labels    = current_labels,
				posterior = posterior[index_of_current_configuration],
				prior     = math.exp(log_prior[index_of_current_configuration]),
				log_BF    = log_BF[index_of_current_configuration],
				BF        = math.exp(log_BF[index_of_current_configuration])
			)
			finemap_summary_list.append(current_finemap_summary)
		return finemap_summary_list


	def normalise_posteriors(self):
		'''
			Return identical OneDConfigurationSample but with updated posteriors that add up to 1
			Arg1: OneDConfigurationSample
			Returntype: OneDConfigurationSample
		'''
		sum_calib = numpy.sum(self.posterior)
		assert not numpy.isinf(sum_calib), 'going to infinity'
		return OneDConfigurationSample(
				configurations = self.configurations,
				posterior = self.posterior / sum_calib,
				log_BF = self.log_BF,
				configuration_size = self.configuration_size,
				log_prior = self.log_prior,
				labels = self.labels,
				sample_label = self.sample_label
			)

	def marginals(self, singleton_count):
		'''
			Return OneDConfigurationSample where the configuration posteriors are reduced to marginals
			on the positions
			Arg2: OneDConfigurationSample
                        Returntype: OneDConfigurationSample
		'''
		singletons = range(singleton_count)
		configurations = dict((i, i) for i in singletons)
		configuration_size=numpy.ones(len(singletons))

		# compute marginal inclusion probability per SNP
		marginal = numpy.zeros(len(singletons))
		for configuration in self.configurations:
			for index in configuration:
				marginal[index] += self.posterior[self.configurations[configuration]]

		return OneDConfigurationSample(
			configurations = configurations,
			posterior = marginal,
			log_BF = None,
			configuration_size = configuration_size,
			log_prior = None,
			sample_label = self.sample_label
		)



	def multiple_marginals(self, singleton_count, kmax):
		'''
			INPUT----
			OneDConfigurationSample self
			Integer kmax
			Integer singleton_count
			OUTPUT------
			Dictionary key range[1, kmax] value OneDConfigurationSample
		'''
		iter_dict = {}
		for nc in range(1,(kmax+1)):
			#print(nc)
			config_iter = [config for config_size in range(nc, nc+1) for config in it.combinations(range(singleton_count), config_size)]
			len_config_iter=len(config_iter)
			configurations = dict((config_iter[i], i) for i in range(len_config_iter))
			configuration_size=numpy.ones(len_config_iter)*nc
			marginal_iter = numpy.zeros(len_config_iter)
			count=0
			input_keys=self.configurations.keys()
			while count < len(self.configurations):
			      	configuration =  input_keys[count]      
      				#print(configuration)
      				if  (len(configuration)<nc): 
	  				count += 1
      				else: 
          				index_tupel =  [config for config in it.combinations(configuration,nc)]
          				for index in index_tupel:
  						marginal_iter[configurations[index]] += self.posterior[self.configurations[configuration]]
				      	count += 1

			iter_out = OneDConfigurationSample(
				configurations = configurations,
				posterior = marginal_iter,
				log_BF = None,
				configuration_size = configuration_size,
				log_prior = None
			)
			iter_dict[nc] = iter_out
		return(iter_dict)

	def create_translation_index(self, from_labels, to_labels):
		
		translate = dict()
		
		for index_in_gwas, current_label in enumerate(from_labels):
			try:
				index_in_eqtl = to_labels.index(current_label)
				translate[index_in_gwas] = index_in_eqtl
			except ValueError:
				translate[index_in_gwas] = None
		
		return translate

	def assert_translation_index_ok(self, translation_index, from_labels, to_labels):

		# Method side effect: Collects and returns some stats along the way.
		
		num_translated   = 0
		num_untranslated = 0
		
		for key in translation_index.keys():
			
			gwas_label = from_labels[key]
			if translation_index[key] is None:
				num_untranslated += 1
				continue
			
			num_translated += 1
			eqtl_label = to_labels[translation_index[key]]
			
			if gwas_label != eqtl_label:
				raise TranslationIndexException
		
		return num_translated, num_untranslated

	def assert_inverse_translation_ok(self, translation, inverse_translation):
		
		for key in translation.keys():
			if translation[key] is None:
				continue
			if key == inverse_translation[translation[key]]:
				continue
			raise TranslationInverseException

	def translate_configuration(translation_index, configurations):
		
		translated_configuration = dict()
		
		for configuration in configurations.keys():
			
			translated_configuration_indexes = []
			
			for configuration_component in configuration:
				translated_configuration_indexes.append( translation_index[ configuration_component ] )
			
			translated_tuple = tuple(translated_configuration_indexes)
			translated_configuration[ translated_tuple ] = configurations[ configuration ]
			
		return translated_configuration

	def translate_configuration(self, translation_index, configurations):
		
		translated_configuration = dict()
		
		for configuration in configurations.keys():
			
			translated_configuration_indexes = []
			
			for configuration_component in configuration:
				translated_configuration_indexes.append( translation_index[ configuration_component ] )
			
			translated_tuple = tuple(translated_configuration_indexes)
			translated_configuration[ translated_tuple ] = configurations[ configuration ]
			
		return translated_configuration

	def joint_posterior(self, sample2):
		'''
			Main function for fine-mapping of two traits
			Arg1: OneDConfigurationSample
			Arg2: OneDConfigurationSample
			Returntype: (float (the overall evidence for shared causal variation at a locus), TwoDConfigurationSample)
		'''
		
		sample1_labels = self.labels
		sample2_labels = sample2.labels
		
		translate_from_sample1_to_sample2 = self.create_translation_index(
			from_labels = sample1_labels,
			to_labels   = sample2_labels
		)
		
		self.assert_translation_index_ok(
			translation_index = translate_from_sample1_to_sample2,
			from_labels       = sample1_labels,
			to_labels         = sample2_labels
		)
		
		translate_from_sample2_to_sample1 = self.create_translation_index(
			from_labels = sample2_labels,
			to_labels   = sample1_labels
		)

		self.assert_translation_index_ok(
			translation_index = translate_from_sample2_to_sample1,
			from_labels       = sample2_labels,
			to_labels         = sample1_labels
		)
		
		self.assert_inverse_translation_ok(
			translation         = translate_from_sample1_to_sample2,
			inverse_translation = translate_from_sample2_to_sample1
		)
		
		translated_sample2_configurations = self.translate_configuration(
			translation_index = translate_from_sample2_to_sample1,
			configurations    = sample2.configurations
		)

		keys1 = set(self.configurations.keys())
		#keys2 = set(sample2.configurations.keys())
		translated_keys2 = set(translated_sample2_configurations.keys())
		
		intersection = list(keys1 & translated_keys2)
		configurations = dict((configuration, index) for index, configuration in enumerate(intersection))
		ids1 = [self.configurations[configuration] for configuration in intersection]
		#ids2 = [sample2.configurations[configuration] for configuration in intersection]
		
		# Only the keys were translated, the values still have the original indexes for the sample2 object.
		ids2 = [translated_sample2_configurations[configuration] for configuration in intersection]
		
		#sample1_labels = [self.labels[configuration] for configuration in intersection]
		
		posterior1 = numpy.take(self.posterior, ids1)
		posterior2 = numpy.take(sample2.posterior, ids2)
		#log_BF1 = numpy.take(self.log_BF, ids1)
		#log_BF2 = numpy.take(sample2.log_BF, ids2)
		#log_prior1 = numpy.take(self.log_prior, ids1)
		#log_prior2 = numpy.take(sample2.log_prior, ids2)
		configuration_size = numpy.take(self.configuration_size, ids1)

		posterior = posterior1 * posterior2
		coloc_evidence = numpy.sum(posterior)

		res_final = TwoDConfigurationSample(
				configurations = configurations,
				posterior = posterior,
				configuration_size = configuration_size,
				posterior1 = posterior1,
				#log_BF1 = log_BF1,
				#log_prior1 = log_prior1,
				posterior2 = posterior2,
				#log_BF2 = log_BF2,
				#log_prior2 = log_prior2
				labels = self.labels,
				#labels = sample1_labels
				coloc_evidence = coloc_evidence,
				sample_1_label = self.sample_label,
				sample_2_label = sample2.sample_label,
		)

		return res_final

TwoDConfigurationSample_prototype = namedtuple(
	'TwoDConfigurationSample_prototype', 
	[
		'configurations', 
		'posterior', 
		'configuration_size', 
		'posterior1', 
		'posterior2', 
		'labels', 
		'coloc_evidence',
		'sample_1_label',
		'sample_2_label'
	]
)
TwoDConfigurationSample_prototype.__new__.__defaults__ = (
	None, 
	None,
	None, 
	None,
	None, 
	None,
	None, 
	"sample1",
	"sample2"
)

#TwoDConfigurationSample = namedtuple('TwoDConfigurationSample', ['configurations', 'posterior', 'configuration_size', 'posterior1', 'log_BF1','log_prior1', 'posterior2', 'log_BF2','log_prior2'])
'''
	Stores colocalisation data on a set of configurations:
	configurations: dict(tuple => int); assigns to each configuration (tuple of indices) an index into the vectors below
	posterior: numpy.array (1D), joint posterior
	configuration_size: numpy.array (1D), number of SNPs in the corresponding vector
	posterior1: numpy.array (1D)
	log_BF1: numpy.array (1D)
	log_prior1: numpy.array (1D)
	posterior2: numpy.array (1D)
	log_BF2: numpy.array (1D)
	log_prior2: numpy.array (1D)
'''

import collections
TwoDConfigurationSample_summary = collections.namedtuple(
	'TwoDConfigurationSample_summary', [
		'labels', 
		'posterior',
		'posterior1',
		'posterior2'
	]
)

class TwoDConfigurationSample(TwoDConfigurationSample_prototype):
	
	def __str__(self):
		return self.to_String()

	def to_String(self, max_show_at_top = 5, max_show_at_end = 2):
		
		summary_list = self.create_summaries()

		summary_list_sorted = sorted(
			summary_list, 
			cmp = lambda x,y: cmp(x.posterior, y.posterior),
			reverse = False
		)
		
		total_configurations = len(summary_list_sorted)
		
		num_show_at_top = min(total_configurations, max_show_at_top)
		num_show_at_end = min(total_configurations, max_show_at_end)
		
		indentation = "    "

		summary_lines = [ "A total of %i configurations have been investigated in %s and %s:" % (total_configurations, self.sample_1_label, self.sample_2_label) ]

		for index in range(num_show_at_top):
			summary_lines.append(indentation + "- " + self.twoDConfigurationSample_summary_to_string(summary_list_sorted[index]))
		
		if num_show_at_top<total_configurations:
		
			summary_lines.append(indentation +  "...")

			for index in range(total_configurations-num_show_at_end, total_configurations):
				summary_lines.append(indentation + "- " + self.twoDConfigurationSample_summary_to_string(summary_list_sorted[index]))
		
		summary_lines.append("The coloc evidence is: {:2e}".format(self.coloc_evidence))
		
		return '\n'.join(summary_lines)

	def create_summaries(self):
		
		summary_list = []
		
		for current_configuration in self.configurations.keys():
			
			snp_labels = ", ".join(self.lookup_labels_for_snp_configuration(current_configuration))
			index = self.configurations[ current_configuration ]
			
			twoDConfigurationSample_summary = TwoDConfigurationSample_summary(
				labels     = snp_labels,
				posterior  = self.posterior[index],
				posterior1 = self.posterior1[index],
				posterior2 = self.posterior2[index]
			)
			summary_list.append( twoDConfigurationSample_summary )
		
		return summary_list
		
	
	def twoDConfigurationSample_summary_to_string(self, twoDConfigurationSample_summary):
		
		sentence = "The snp configuration ({}) had posterior probabilities of {:.2e} in {} and {:.2e} in {}. The joint posterior probability is {:.2e}.".format(
			twoDConfigurationSample_summary.labels,
			float(twoDConfigurationSample_summary.posterior1),
			self.sample_1_label,
			float(twoDConfigurationSample_summary.posterior2),
			self.sample_2_label,
			float(twoDConfigurationSample_summary.posterior),
		)
		
		return sentence

	
	def lookup_labels_for_snp_configuration(self, configuration):
		'''
			Copied over: not good!
		'''
		
		labels = []
		
		for position, configuration_index in enumerate(configuration):
			labels.append(self.labels[configuration_index])
		
		return labels

def finemap(z_scores, cov_matrix, n, labels, kstart=1, kmax=5, max_iter=100000, output="configuration", prior="independence", v_scale=0.0025, g="BRIC", verbose=False, sample_label="Unnamed sample"):
	'''
		Main function for fine-mapping using stochastic search for one trait #
		Arg1: z-scores: numpy.array
		Arg2: cov_matrix numpy.array, correlation-structure (TwoD) array
		Arg3: n: int, sample size
		Arg kstart: int, full exploration of sets with #kstart causal variants
		Arg kmax: int, maximum number of causal variants
		Arg max_iter: int, iterations of stochastic search
		Arg prior= string ("independence" or "gprior")
		Arg v_scale = float, prior variance of the independence prior, recommended 0.05 **2 (following FINEMAP, Benner et al 2016)
		Arg g: string, g-parameter of the g-prior, recommended g="BRIC" g=max(n,#SNPs**2), other options g="BIC" where g=n (Bayes Information Criterion), or  g="RIC" where g=#SNPs**2 (Risk Inflation Criterion) see Mixtures of g Priors for Bayesian Variable Selection Liang et al 2008
		Arg verbose = False: boolean, print the progress of the stochastic search
		Returntype: OneDConfigurationSample
	'''

	# Test inputs
	assert len(z_scores) == cov_matrix.shape[0], 'Covariance matrix has %i rows, %i expcted' % (cov_matrix.shape[0], len(z_scores))
	assert len(z_scores) == cov_matrix.shape[1], 'Covariance matrix has %i columns, %i expcted' % (cov_matrix.shape[0], len(z_scores))
	assert not kstart > kmax, 'Incorrect number of causal variants specified, kmax (%i) must be greater than kstart (%s)' % (kmax, kstart)
	assert not numpy.any(numpy.isnan(z_scores)), 'Missing values detected in z-scores'
	assert not numpy.any(numpy.isnan(cov_matrix)), 'Missing values detected in covariance matrix'

	# Initialise
	score_cache = dict()
	neighbourhood_cache = dict()
	configurations = [config for config_size in range(1, kstart + 1) for config in it.combinations(range(len(z_scores)), config_size)]
	results = compare_neighborhood(
		configs  = configurations, 
		z_scores = z_scores, 
		cov_matrix = cov_matrix, 
		kmax = kmax, 
		n = n, 
		score_cache = score_cache, 
		prior = prior, 
		v_scale = v_scale, 
		g = g, 
		labels=labels,
		sample_label = sample_label
	)

	# Simple search
	if kstart == kmax:
		res_out=results.normalise_posteriors()

		if output == "configuration":
			return res_out
		elif output == "marginal":
			return res_out.marginals(len(z_scores))
		else:
			assert False, "%s unkown" % {output}


	# shotgun stochastic search
	if kstart < kmax:
		p = results.normalise_posteriors().posterior
		current_config = configurations[numpy.random.choice(len(p), size=1, p=p)[0]]
		count = 1
		result_list = [results]
		while count < max_iter:
			# Generate new configs
			new_configs = create_neighborhood(current_config, len(z_scores), kstart, kmax, neighbourhood_cache)

			# Evaluate probabilities of these configs
			results_nh = compare_neighborhood(new_configs, z_scores, cov_matrix, kmax, n, score_cache, prior, v_scale=v_scale, g=g, labels=labels)

			# Add new entries into the results list
			result_list.append(results_nh)

			# Choose seed for next round among new configs
			prob = results_nh.normalise_posteriors().posterior
			current_config = new_configs[numpy.random.choice(len(new_configs), size=1, p=prob)[0]]

			# Chatter to stdout
			if verbose == True:
				print(str(numpy.round(float(count) / max_iter * 100)) + '% of the search done')
				print(current_config)

			# Keep count of sampled configs
			count += 1

		res_out = merge_samples(result_list).normalise_posteriors()

		if output == "configuration":
			return res_out
		elif output == "marginal":
			return res_out.marginals(len(z_scores))
		else:
			assert False, "%s unkown" % {output}

def create_neighborhood(current_config, m, kstart, kmax, neighbourhood_cache):
	'''
		Defines a new set of possible moves starting from current config
		1. add
		2. swap
		3. delete
		Arg1: np.array (a possible starting causal configuration)
		Arg2: int, the size of the locus
		Arg3: int
		Arg4: int
		Returntype: array[arrays], other possible causal configurations
	'''
	if tuple(current_config) in neighbourhood_cache:
		return neighbourhood_cache[tuple(current_config)]	
	current_size = len(current_config)
	new_configs = []
	if current_size <= kstart:
		# add move (m-k new possible config)
		for i in range(m):
			new_possible_config = numpy.append(current_config, i)
			new_possible_config.sort()
			new_possible_config = numpy.unique(new_possible_config)
			new_configs.append(new_possible_config)
		# swap move k(m-k)
		for i in range(current_size):
			for j in range(m):
				new_possible_config = numpy.delete(current_config, i)
				new_possible_config = numpy.append(new_possible_config, j)
				new_possible_config.sort()
				new_possible_config = numpy.unique(new_possible_config)
				new_configs.append(new_possible_config)
	if current_size > kstart and current_size < kmax:
		# delete move (k new possible config)
		for i in range(current_size):
			new_possible_config = numpy.delete(current_config, i)
			new_configs.append(new_possible_config)
		# add move (m-k new possible config)
		for i in range(m):
			new_possible_config = numpy.append(current_config, i)
			new_possible_config.sort()
			new_possible_config = numpy.unique(new_possible_config)
			new_configs.append(new_possible_config)
		# swap move k(m-k)
		for i in range(current_size):
			for j in range(m):
				new_possible_config = numpy.delete(current_config, i)
				new_possible_config = numpy.append(new_possible_config, j)
				new_possible_config.sort()
				new_possible_config = numpy.unique(new_possible_config)
				new_configs.append(new_possible_config)
	if current_size == kmax:
		# delete move (k new possible config)
		for i in range(current_size):
			new_possible_config = numpy.delete(current_config, i)
			new_configs.append(new_possible_config)
		# swap move k(m-k)
		for i in range(current_size):
			for j in range(m):
				new_possible_config = numpy.delete(current_config, i)
				new_possible_config = numpy.append(new_possible_config, j)
				new_possible_config.sort()
				new_possible_config = numpy.unique(new_possible_config)
				new_configs.append(new_possible_config)

	neighbourhood_cache[tuple(current_config)] = new_configs	
	return new_configs

def compare_neighborhood(configs, z_scores, cov_matrix, kmax, n, score_cache, labels, prior="independence", v_scale=0.0025, g="BRIC", sample_label="Unnamed sample"):
	'''
		Compare the moves with respect to the unscaled log posterior probability
		Arg1: array of arrays
		Arg2: numpy.array (OneD)
		Arg3: numpy.array (TwoD)
		Arg4: kmax: int, maximum number of causal SNPs
		Arg5: n: int, sample size
		Arg prior: string, "independence" or "gprior"
		Arg v_scale = float, prior variance of the independence prior, recommended 0.05**2 (following FINEMAP, Benner et al 2016)
		Arg g: string, g-parameter of the g-prior, recommended g="BRIC" g=max(n,#SNPs**2), other options g="BIC" where g=n (Bayes Information Criterion), or  g="RIC" where g=#SNPs**2 (Risk Inflation Criterion) see Mixtures of g Priors for Bayesian Variable Selection Liang et al 2008
	'''
	nh_size = len(configs)
	configuration_size = numpy.array([len(configuration) for configuration in configs])
	log_prior = calc_logbinom(configuration_size, kmax, len(z_scores))
	log_BF = numpy.zeros(len(configs))
	i=0

	for configuration in configs:
		if tuple(configuration) in score_cache:
			log_BF[i] = score_cache[tuple(configuration)]
			i=i+1
			continue

		z_tuple = numpy.take(z_scores, configuration)
		cov_tuple = cov_matrix[numpy.ix_(configuration, configuration)]
		tuple_size = len(z_tuple)
		if prior == "independence":
			v = numpy.eye(tuple_size) * v_scale
			log_BF[i] = calc_logBF(z_tuple, cov_tuple, v, n)
		elif prior == "gprior":
			log_BF[i] = calc_loggBF(z_tuple, cov_tuple, g, n)
		else:
			assert False, "%s is not one of independence or gprior" % (prior)
		score_cache[tuple(configuration)] = log_BF[i]
		i = i+1

	return OneDConfigurationSample(
			configurations = dict((tuple(config), index) for index, config in enumerate(configs)),
			posterior = numpy.exp(log_BF + log_prior),
			log_BF = log_BF,
			configuration_size = configuration_size,
			log_prior = log_prior,
			labels = labels,
			sample_label = sample_label
		)

def calc_logBF(z, cov, v, n):
	'''
		Compute Bayes Factors with assumption of independent variances
		Arg1: numpy.array (1D)
		Arg2: numpy.array (2D)
		Arg3: numpy.array diagonal matrix of prior variances
		Arg4: int sample size
		Returntype: numpy.array
	'''
	z = numpy.matrix(z)
	v = numpy.matrix(v)
	m = z.shape[1]
	coeff = 1. / math.sqrt(numpy.linalg.det((numpy.matrix(numpy.eye(m)) + n * numpy.matrix(v) * numpy.matrix(cov))))
	exponent = 0.5 * z * \
		numpy.matrix(numpy.linalg.pinv(((n * v).I + cov), 0.0001)) * z.T
	return numpy.array(numpy.log(coeff) + exponent)[0][0]

def calc_loggBF(z, cov, n, g="BRIC"):
	'''
		Compute Bayes Factors with gprior method
		Arg1: numpy.array (1D)
		Arg2: numpy.array (2D)
		Arg3: int sample size
                Arg g: string, g-parameter of the g-prior, recommended g="BRIC" g=max(n,#SNPs**2), other options g="BIC" where g=n (Bayes Information Criterion), or  g="RIC" where g=#SNPs**2 (Risk Inflation Criterion) see Mixtures of g Priors for Bayesian Variable Selection Liang et al 2008
		Returntype: numpy.array
	'''
        if(g=="BRIC"):
           gp=numpy.max((len(z),n))
        if(g=="BIC"):
	   gp=n
        if(g=="RIC"):
	   gp=len(z)
        z = numpy.matrix(z)
	cov = numpy.matrix(cov)
	m = numpy.float(len(z))
	gp = numpy.float(gp)
	pinv = numpy.matrix(numpy.linalg.pinv(cov, 0.0001))
	coeff = (1 + gp)**(-m / 2)
	exponent = 0.5 * numpy.divide(gp, (gp + 1)) * z * pinv * z.T
	return numpy.array((math.log(coeff) + exponent))[0][0]


def calc_logbinom(subset_size, k, m):
	'''
                creates a binomial prior for a given subset_size under the assumption of k causal variants 
                excluding k=0 (that is no causal variant)
		Arg1: numpy.array (1D)
		Arg2: int, maximum number of causal variants
		Arg3: int, number of SNPs (len(z))
		Returntype: float
	'''
	if k == 1:
		return numpy.zeros(m)
	else:
		p = float(1) / m
		p_binom = p**subset_size * (1 - p)**(m - subset_size)
		p_k = numpy.zeros(k - 1)
		for i in range(1, k):
			p_k[i - 1] = p**i * (1 - p)**(m - i)
		p_rescale = numpy.sum(p_k)
		p_out = p_binom / p_rescale
		return numpy.log(p_out)

def merge_samples(samples):
	'''
		Return merged OneDConfigurationSample
		Arg1: [ OneDConfigurationSample ]
		Returntype: OneDConfigurationSample
	'''
	configurations_old = dict((configuration, (sample, sample.configurations[configuration])) for sample in samples for configuration in sample.configurations)
	configurations = dict((configuration, index) for index, configuration in enumerate(configurations_old.keys()))

	posterior = numpy.zeros(len(configurations))
	configuration_size = numpy.zeros(len(configurations))
	log_BF = numpy.zeros(len(configurations))
	log_prior = numpy.zeros(len(configurations))

	for configuration in configurations:
		sample, old_index = configurations_old[configuration]
		new_index = configurations[configuration]
		posterior[new_index] = sample.posterior[old_index]
		configuration_size[new_index] = sample.configuration_size[old_index]
		log_BF[new_index] = sample.log_BF[old_index]
		log_prior[new_index] = sample.log_prior[old_index]

	return OneDConfigurationSample(
			configurations = configurations,
			posterior = posterior,
			log_BF = log_BF,
			configuration_size = configuration_size,
			log_prior = log_prior
		)
