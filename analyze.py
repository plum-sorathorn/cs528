import re
from concurrent.futures import ThreadPoolExecutor
import time
import statistics
import numpy as np
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

LINK_TEXT = re.compile(r'href\s*=\s*["\'](\d+)\.html["\']', re.IGNORECASE)

class GraphAnalyzer:
    def __init__(self):
        self.graph = {}  # Format: {page_id: [list_of_outgoing_links]}
        self.in_links = defaultdict(list) # Format: {target_id: [list_of_source_ids]}
        self.out_degrees = {}
        self.pages = []
        self.n = 0

    def load_from_bucket(self, bucket_name, prefix="", max_workers=20):
        """
        Fast, Cloud-Shell-safe, threaded GCS loader.
        """
        print(f"Connecting to bucket: {bucket_name}")
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        self.graph.clear()
        self.in_links.clear()
        self.out_degrees.clear()

        start_time = time.time()
        count = 0

        def download_and_parse(blob):
            # Skip directory markers and non-html
            if not blob.name.endswith(".html"):
                return None

            try:
                page_id = blob.name.split("/")[-1]
                content = blob.download_as_bytes().decode("utf-8", errors="ignore")

                # Extract real links only
                targets = LINK_TEXT.findall(content)
                targets = [f"{t}.html" for t in targets]

                return page_id, targets
            except Exception:
                return None

        blob_iter = bucket.list_blobs(prefix=prefix)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(download_and_parse, blob_iter):
                if result is None:
                    continue

                page_id, links = result
                self.graph[page_id] = links
                self.out_degrees[page_id] = len(links)

                for tgt in links:
                    self.in_links[tgt].append(page_id)
                    if tgt not in self.out_degrees:
                        self.out_degrees[tgt] = 0

                count += 1
                if count % 5000 == 0:
                    elapsed = time.time() - start_time
                    print(f"Processed {count} files ({elapsed:.1f}s)")

        self.pages = list(self.out_degrees.keys())
        self.n = len(self.pages)

        print(f"Graph built: {self.n} pages in {time.time() - start_time:.2f} seconds")

    def compute_stats(self):
        """Computes Average, Median, Max, Min, and Quintiles for In/Out degrees."""
        if self.n == 0:
            return "No data loaded."

        in_degree_vals = [len(self.in_links[p]) for p in self.pages]
        out_degree_vals = [self.out_degrees[p] for p in self.pages]

        def get_metrics(data, label):
            if not data: return
            q = np.percentile(data, [0, 20, 40, 60, 80, 100])
            print(f"\n {label} Statistics ")
            print(f"Average: {statistics.mean(data):.2f}")
            print(f"Median:  {statistics.median(data)}")
            print(f"Max:     {max(data)}")
            print(f"Min:     {min(data)}")
            print(f"Quintiles (0%, 20%, 40%, 60%, 80%, 100%): {q}")

        get_metrics(in_degree_vals, "Incoming Links")
        get_metrics(out_degree_vals, "Outgoing Links")

    def run_pagerank(self, damping=0.85, tol=0.005):
        """
        Iterative PageRank: 
        PR(A) = 0.15/n + 0.85 * sum(PR(Ti)/C(Ti))
        """
        print(f"\n Starting PageRank (N={self.n}) ")
        
        # Initialize PR to 1/n
        initial_pr = 1.0 / self.n
        pagerank = {page: initial_pr for page in self.pages}
        
        iteration = 0
        base_score = (1 - damping) / self.n

        while True:
            iteration += 1
            new_pagerank = {}
            total_pr_sum = 0
            
            for page in self.pages:
                incoming_sum = 0
                # Find all T_i pointing to page
                for source in self.in_links[page]:
                    c_ti = self.out_degrees[source]
                    if c_ti > 0:
                        incoming_sum += pagerank[source] / c_ti
                
                # Apply Formula
                pr_val = base_score + (damping * incoming_sum)
                new_pagerank[page] = pr_val
                total_pr_sum += pr_val

            # Check Convergence: "Sum of pageranks across all pages does not change by more than 0.5%"
            # Interpretation: sum(|new - old|) / sum(new) < 0.005? 
            # Or strictly check if the total mass change is minimal?
            # Standard PR checks L1 norm of the difference vector.
            
            diff_sum = sum(abs(new_pagerank[p] - pagerank[p]) for p in self.pages)
            total_mass = sum(new_pagerank.values())
            
            # Use percent change of the diff relative to total mass
            change_percent = (diff_sum / total_mass) * 100 if total_mass > 0 else 0
            
            print(f"Iteration {iteration}: Total Mass={total_mass:.4f}, Delta={diff_sum:.6f} ({change_percent:.4f}%)")

            pagerank = new_pagerank

            if change_percent < (tol * 100):
                print("Convergence reached.")
                break
            
            # Safety break for huge graphs if not converging
            if iteration > 100:
                print("Max iterations reached.")
                break

        return pagerank

    def print_top_5(self, pagerank):
        sorted_pr = sorted(pagerank.items(), key=lambda item: item[1], reverse=True)
        print("\n Top 5 Pages by PageRank ")
        for rank, (page, score) in enumerate(sorted_pr[:5], 1):
            print(f"{rank}. {page}: {score:.8f}")

#  Testing Section 
def run_tests():
    print("RUNNING INDEPENDENT VERIFICATION TESTS")
    
    # Create a known small graph
    # A -> B, C
    # B -> C
    # C -> A
    # N = 3
    
    analyzer = GraphAnalyzer()
    analyzer.graph = {
        'A': ['B', 'C'],
        'B': ['C'],
        'C': ['A']
    }
    analyzer.pages = ['A', 'B', 'C']
    analyzer.n = 3
    
    # Manually set up helper structures
    analyzer.out_degrees = {'A': 2, 'B': 1, 'C': 1}
    analyzer.in_links = {
        'A': ['C'],
        'B': ['A'],
        'C': ['A', 'B']
    }

    print("Test Graph: A->[B,C], B->[C], C->[A]")
    
    pr_results = analyzer.run_pagerank(tol=0.005)
    
    print("Final PR Scores:", pr_results)
    
    # Check if they sum roughly to 1 (or near it depending on sink nodes)
    total = sum(pr_results.values())
    assert 0.99 < total < 1.01, f"Total Probability Mass lost! Sum: {total}"
    
    # Based on graph topology, C should be highest (gets inputs from A and B)
    # A gets input from C
    # B gets input only from half of A
    assert pr_results['C'] > pr_results['A'], "Logic Error: C should have higher rank than A"
    assert pr_results['A'] > pr_results['B'], "Logic Error: A should have higher rank than B"
    
    print("TEST PASSED: Graph logic and rank order verified.")

if __name__ == "__main__":
    # run the test first
    run_tests()

    # define bucket name
    BUCKET_NAME = "cs528-plum-hw2" 
    
    
    total_start = time.time() # start timer
    
    analyzer = GraphAnalyzer()
    try:
        # I/O Timing (Downloading and Parsing)
        io_start = time.time()
        analyzer.load_from_bucket(BUCKET_NAME, prefix="", max_workers=100)
        io_duration = time.time() - io_start
        
        # Stats Timing
        analyzer.compute_stats()
        
        # PageRank Computation Timing
        pr_start = time.time()
        final_pr = analyzer.run_pagerank()
        pr_duration = time.time() - pr_start
        
        # Output Results
        analyzer.print_top_5(final_pr)
        
        total_duration = time.time() - total_start
        
        # FINAL TIMING REPORT FOR YOUR ASSIGNMENT
        print("PERFORMANCE TIMING REPORT")
        print(f"I/O & Graph Construction: {io_duration:.2f} seconds")
        print(f"PageRank Computation:     {pr_duration:.2f} seconds")
        print(f"Total Execution Time:     {total_duration:.2f} seconds")
        
    except Exception as e:
        print(f"An error occurred: {e}")