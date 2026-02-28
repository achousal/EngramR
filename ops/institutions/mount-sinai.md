---
type: "institution"
name: "Icahn School of Medicine at Mount Sinai"
slug: "mount-sinai"
departments:
  - name: "Department of Oncological Sciences"
    type: "basic_science"
  - name: "Department of Medicine"
    type: "clinical"
  - name: "Department of Neurology"
    type: "clinical"
  - name: "Department of Genetics and Genomic Sciences"
    type: "basic_science"
  - name: "Department of Microbiology"
    type: "basic_science"
  - name: "Department of Artificial Intelligence and Human Health"
    type: "computational"
centers:
  - "Tisch Cancer Institute"
  - "Alzheimer's Disease Research Center (ADRC)"
  - "Friedman Brain Institute"
  - "Institute for Genomics and Multiscale Biology"
  - "Center for Biostatistics"
  - "Hasso Plattner Institute for Digital Health"
compute:
  - name: "Minerva"
    type: "HPC"
    scheduler: "LSF"
    notes: "Rocky 9 nodes; paths under /sc/arion/projects/; bsub job arrays and dependencies supported"
core_facilities:
  - "Genomics Core (RNA-seq, ATAC-seq, scRNA-seq)"
  - "Quantitative Proteomics Core (Olink, SomaScan, mass spec)"
  - "Flow Cytometry Core"
  - "Biorepository and Pathology Core"
  - "Advanced Imaging Center"
platforms:
  - "REDCap (clinical data management)"
  - "BioMe Biobank (internal biobank cohort)"
  - "Mount Sinai Data Warehouse (EHR data)"
  - "Synapse (data sharing platform)"
shared_resources:
  - "BioMe Biobank -- multi-ethnic biobank with EHR linkage (~50,000 participants)"
  - "ADRC cohort -- longitudinal Alzheimer's disease research cohort"
  - "MarkVCID consortium -- vascular contributions to cognitive impairment"
  - "MCC Cohort (REDCap) -- kidney/CKD research cohort"
source_urls:
  - "https://www.mountsinai.org/research/cores"
  - "https://icahn.mssm.edu/research/genomics"
  - "https://hpc.mssm.edu"
last_fetched: "2026-02-28"
created: "2026-02-28"
updated: "2026-02-28"
tags: ["institution"]
---

## Compute Resources

Minerva HPC cluster (Rocky 9) is the primary compute resource. Accessible via LSF scheduler (`bsub`). Project paths are organized under `/sc/arion/projects/`. Conda and module-based environments are supported. Singularity containers are available for reproducible workflows.

## Core Facilities

- **Genomics Core**: Illumina short-read sequencing for RNA-seq, ATAC-seq, WGS, ChIP-seq, and 10x single-cell platforms.
- **Quantitative Proteomics Core**: Olink proximity extension assay, SomaScan aptamer-based proteomics, and mass spectrometry-based proteomics.
- **Flow Cytometry Core**: Cell sorting and immunophenotyping.
- **Biorepository and Pathology Core**: Tissue banking, biospecimen processing.
- **Advanced Imaging Center**: Confocal, super-resolution, and live-cell imaging.

## Platforms and Databases

- **REDCap**: Secure web-based clinical data management system used across multiple cohort studies.
- **BioMe Biobank**: Mount Sinai's multi-ethnic biobank with electronic health record linkage, ~50,000 consented participants.
- **Mount Sinai Data Warehouse**: Centralized EHR repository for clinical data pulls.
- **Synapse**: Collaborative data sharing and analysis platform.

## Biobanks and Cohorts

- **BioMe Biobank**: Multi-ethnic, EHR-linked biobank; primary resource for population-level biomarker studies.
- **ADRC cohort**: NIH-funded longitudinal cohort for Alzheimer's disease biomarker research, coordinated through the Mount Sinai ADRC.
- **MarkVCID**: Multi-site consortium studying vascular contributions to cognitive impairment and dementia.
- **VascBrain CADASIL cohort**: Institutional cohort for cerebral autosomal dominant arteriopathy with subcortical infarcts and leukoencephalopathy (CADASIL) research.
