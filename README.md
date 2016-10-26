CTTV 24 Project
===============

Copyright holder: [EMBL-European Bioinformatics Institute](http://www.ebi.ac.uk) (Apache 2 License)

This script is designed to automatically finemap and highlight the causal variants behind GWAS results by cross-examining GWAS, population genetic, epigenetic and cis-regulatory datasets.

Its original design was based on [STOPGAP](). 

Installing dependencies
-----------------------

To install all dependencies run ```sh install_dependencies.sh```

Add the the following directories to your ```$PATH``` environment variable:
- bin
- scripts
- scripts/preprocessing

Dataset Preprocessing
---------------------

* Via the FTP site (*recommended*)
Download all the files on the OpenTargets FTP site (URL TBD)

* Manually (*sloooow*)
  1. Type ```make download``` to download public databases.
  2. Type ```make process_databases``` to preprocess the databases. 
  3. Type ```make process_1000G``` to preprocess 1000Genomes data from the raw vcf.gz files.

Running
-------

By default, run from the root directory the command: 

```
python scripts/gwas_to_genes.py --disease autism  
```

Multiple disease names can be provided.

Testing
-------

(Under construction)
```
sh scripts/testing/test_all_efos.sh > table.tsv
```

