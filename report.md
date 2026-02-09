# CS528 Homework 2: PageRank & Cloud Storage Analysis

**Name:** [Your Name]  
**Date:** February 9, 2026  
**GitHub Repository:** [https://github.com/plum-sorathorn/cs528/](https://github.com/plum-sorathorn/cs528/)

## 1. Infrastructure Setup

### Bucket Creation and Data Generation
For this assignment, I created a Google Cloud Storage bucket named `cs528-plum-hw2` located in the `us-central1` region. This region was chosen to minimize latency and costs associated with cross-region data transfer.

1.  **File Generation:** I used the provided `generate-content.py` script to generate the synthetic web graph dataset.
    * **Command:** `python generate-content.py -n 20000 -m 375`
    * **Result:** This created 20,000 HTML files, each containing random text and a variable number of links (up to 375) pointing to other files in the set.

2.  **Upload to Cloud:** I uploaded these files to the bucket using the Google Cloud SDK `gsutil` tool. I used the `-m` flag to enable multi-threading, which significantly sped up the upload of 20,000 small files.
    * **Command:** `gsutil -m cp *.html gs://cs528-plum-hw2/data/`

### Permissions (ACLs)
To ensure the bucket was accessible for testing by TFs and my scripts, I configured the Access Control Lists (ACLs) to be world-readable.

* **Action:** I granted `Storage Object Viewer` permissions to `allUsers` on the bucket.
* **Verification:** I verified accessibility by attempting to download a random file via a standard `curl` command without authentication, confirming that the files are publicly readable as required.

---

## 2. Implementation Details

The core logic is implemented in `analyze.py`. The program performs three main tasks:

1.  **Graph Construction:** The script parses HTML files to build an adjacency list representing the web graph. It uses regular expressions to extract links effectively.

2.  **Statistical Analysis:** It computes the average, median, min, max, and quintiles for both incoming (in-degree) and outgoing (out-degree) links using Python's `statistics` and `numpy` libraries.

3.  **PageRank Computation:** I implemented the iterative PageRank algorithm:
    
    $$PR(A) = \frac{0.15}{N} + 0.85 \sum_{i=1}^{n} \frac{PR(T_i)}{C(T_i)}$$

    * **Damping Factor:** 0.85
    * **Convergence Criteria:** The algorithm iterates until the sum of the absolute differences in PageRank scores across all pages changes by less than 0.5%.

### Verification of Correctness
To ensure the algorithm is correct independent of the randomly generated 20,000-file dataset, I included a deterministic test case in the code (`run_tests` function).

* **Test Graph:** A 3-node graph (A, B, C) with known connections:
    * `A -> [B, C]`
    * `B -> [C]`
    * `C -> [A]`
* **Expected Outcome:** Based on the link structure, Page C should have the highest rank (receiving inputs from A and B), followed by A (receiving input from C), and B should be lowest (receiving input only from half of A).
* **Result:** The code runs this verification before processing the main dataset. The test asserts that `PR(C) > PR(A) > PR(B)`, confirming the logic holds.

---

## 3. Execution and Timing

### Method A: Local Execution
Running the script on my local machine allows for direct streaming from the Google Cloud Storage bucket using the Python client.

* **Command:** `python analyze.py`
* **Environment:** Local Laptop
* **Output:**

```text
Graph built: 20000 pages in 60.59 seconds

--- Incoming Links Statistics ---
Average: 187.06
Median:  187.0
Max:     240
Min:     135
Quintiles (0%, 20%, 40%, 60%, 80%, 100%): [135. 176. 183. 190. 198. 240.]

--- Outgoing Links Statistics ---
Average: 187.06
Median:  187.0
Max:     374
Min:     0
Quintiles (0%, 20%, 40%, 60%, 80%, 100%): [  0.  76. 152. 223. 299. 374.]

--- Starting PageRank (N=20000) ---
Iteration 1: Total Mass=0.9978, Delta=0.081395 (8.1572%)
Iteration 2: Total Mass=0.9961, Delta=0.008512 (0.8546%)
Iteration 3: Total Mass=0.9946, Delta=0.001657 (0.1666%)
Convergence reached.

--- Top 5 Pages by PageRank ---
1. 15441.html: 0.00011508
2. 14576.html: 0.00010481
3. 318.html: 0.00010357
4. 14088.html: 0.00010331
5. 14208.html: 0.00009997

==============================
PERFORMANCE TIMING REPORT
==============================
I/O & Graph Construction: 62.15 seconds
PageRank Computation:     2.08 seconds
Total Execution Time:     64.30 seconds
==============================
```
   

### Method B: Cloud Shell Execution
When running on Google Cloud Shell, I encountered timeout issues when attempting to open thousands of simultaneous HTTP connections via the Python client due to the VM's resource constraints. To resolve this, I adopted a two-step "staging" approach optimized for the Cloud Shell environment:

1.  **Download:** Used three commands to download the 20k files from the bucket
    * You may need to first login with 'gcloud auth login' before using the gcloud storage command
2.  **Process:** Ran `analyze_shell.py` to process the files from the local disk.

* **Commands:**
    ```bash
    mkdir -p hw2_data
    gcloud storage cp gs://cs528-plum-hw2/data/*.html hw2_data/    
    python analyze_shell.py
    ```
* **Output:**

```text
[PASTE YOUR CLOUD SHELL OUTPUT HERE]
```

## 4. Cloud Resource Costs

The development and execution of this project utilized Google Cloud Storage (Class A operations for listing/reading) and Cloud Shell (free tier). The total cost incurred was minimal.

**Total Spend:** $0.00 (or insert actual amount if > 0)

*(Note: Please refer to the attached screenshot showing the billing console view for the relevant dates)*

## 5. Use of AI

I utilized an AI assistant (Gemini) to assist with the following aspects of the assignment:

* **Debugging Network Timeouts:** I consulted the AI when my Python script timed out on Cloud Shell. It explained the concurrency limits of the Cloud Shell VM and suggested using `gsutil` for the download phase as a more robust alternative to Python's `ThreadPoolExecutor` for this specific environment.
* **Code Structure:** I used AI to generate the boilerplate code for the `ThreadPoolExecutor` to ensure thread-safe file downloading and processing.
* **Report Generation:** I used AI to help structure this final report based on the assignment requirements.

I verified all code generated by the AI, specifically the PageRank logic, by writing the independent 3-node graph test case described in Section 2. I understand that the PageRank algorithm distributes probability mass across the graph and that handling "sink" nodes (nodes with no outgoing links) requires care (though in this implementation, we allowed standard damping to handle sinks naturally).