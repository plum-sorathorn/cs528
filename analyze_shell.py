import re
import time
import os
import statistics
import numpy as np
from collections import defaultdict

# Configuration 
DATA_DIR = "hw2_data"  # Must match the directory in the shell script

LINK_TEXT = re.compile(r'href\s*=\s*["\'](\d+)\.html["\']', re.IGNORECASE)

class GraphAnalyzer:
    def __init__(self):
        self.graph = {} 
        self.in_links = defaultdict(list) 
        self.out_degrees = {}
        self.pages = []
        self.n = 0

    def load_from_directory(self, local_dir):
        """
        Reads files from the local directory.
        """
        print(f"Loading Graph from Local Directory: {local_dir} ")
        
        if not os.path.exists(local_dir):
            print(f"Error: Directory '{local_dir}' not found. Did you run the download script?")
            return

        self.graph.clear()
        self.in_links.clear()
        self.out_degrees.clear()

        start_time = time.time()
        files = [f for f in os.listdir(local_dir) if f.endswith(".html")]
        total_files = len(files)
        
        print(f"Found {total_files} files to process.")
        
        count = 0
        for filename in files:
            try:
                page_id = filename
                file_path = os.path.join(local_dir, filename)
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Extract links
                targets = LINK_TEXT.findall(content)
                targets = [f"{t}.html" for t in targets]

                # Build Graph
                self.graph[page_id] = targets
                self.out_degrees[page_id] = len(targets)

                for tgt in targets:
                    self.in_links[tgt].append(page_id)
                    # Initialize out_degree for target if not seen yet
                    if tgt not in self.out_degrees:
                        self.out_degrees[tgt] = 0
                
                count += 1
                if count % 5000 == 0:
                    print(f"Parsed {count} files...")
                    
            except Exception as e:
                print(f"Error reading {filename}: {e}")

        self.pages = list(self.out_degrees.keys())
        self.n = len(self.pages)
        print(f"Graph built: {self.n} pages parsed in {time.time() - start_time:.2f} seconds")

    def compute_stats(self):
        if self.n == 0: return
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
            print(f"Quintiles: {q}")

        get_metrics(in_degree_vals, "Incoming Links")
        get_metrics(out_degree_vals, "Outgoing Links")

    def run_pagerank(self, damping=0.85, tol=0.005):
        print(f"\n Starting PageRank (N={self.n}) ")
        initial_pr = 1.0 / self.n
        pagerank = {page: initial_pr for page in self.pages}
        
        iteration = 0
        base_score = (1 - damping) / self.n

        while True:
            iteration += 1
            new_pagerank = {}
            
            # Optimization: Pre-calculate sum of PR(T)/C(T) for every node
            # However, for 20k nodes, the direct loop below is usually fast enough
            
            for page in self.pages:
                incoming_sum = 0
                for source in self.in_links[page]:
                    c_ti = self.out_degrees[source]
                    if c_ti > 0:
                        incoming_sum += pagerank[source] / c_ti
                
                new_pagerank[page] = base_score + (damping * incoming_sum)

            # Check Convergence
            diff_sum = sum(abs(new_pagerank[p] - pagerank[p]) for p in self.pages)
            total_mass = sum(new_pagerank.values())
            
            # Avoid division by zero
            if total_mass == 0: total_mass = 1 
            
            change_percent = (diff_sum / total_mass) * 100
            
            print(f"Iteration {iteration}: Delta={diff_sum:.6f} ({change_percent:.4f}%)")
            pagerank = new_pagerank

            if change_percent < (tol * 100):
                print("Convergence reached.")
                break
            
            if iteration > 100:
                print("Max iterations reached.")
                break

        return pagerank

    def print_top_5(self, pagerank):
        sorted_pr = sorted(pagerank.items(), key=lambda item: item[1], reverse=True)
        print("\n Top 5 Pages by PageRank ")
        for rank, (page, score) in enumerate(sorted_pr[:5], 1):
            print(f"{rank}. {page}: {score:.8f}")

# Testing Section 
def run_tests():
    print("RUNNING INDEPENDENT VERIFICATION TESTS")
    
    analyzer = GraphAnalyzer()
    analyzer.graph = {'A': ['B', 'C'], 'B': ['C'], 'C': ['A']}
    analyzer.pages = ['A', 'B', 'C']
    analyzer.n = 3
    analyzer.out_degrees = {'A': 2, 'B': 1, 'C': 1}
    analyzer.in_links = {'A': ['C'], 'B': ['A'], 'C': ['A', 'B']}

    print("Test Graph: A->[B,C], B->[C], C->[A]")
    pr_results = analyzer.run_pagerank(tol=0.005)
    print("Final PR Scores:", pr_results)
    
    assert pr_results['C'] > pr_results['A'], "Logic Error: C should be > A"
    assert pr_results['A'] > pr_results['B'], "Logic Error: A should be > B"
    print("TEST PASSED\n")

if __name__ == "__main__":
    run_tests()
    
    total_start = time.time()
    analyzer = GraphAnalyzer()

    try:
        parse_start = time.time()
        analyzer.load_from_directory(DATA_DIR)
        analyzer.compute_stats()
        parse_duration = time.time() - parse_start
        
        if analyzer.n > 0:
            pr_start = time.time()
            final_pr = analyzer.run_pagerank()
            pr_duration = time.time() - pr_start
            
            analyzer.print_top_5(final_pr)
            
            total_duration = time.time() - total_start
            
            print("PERFORMANCE TIMING REPORT")
            print(f"Parsing/Stats Time:   {parse_duration:.2f} s")
            print(f"PageRank Time:        {pr_duration:.2f} s")
            print(f"Total Execution Time: {total_duration:.2f} s")
            print("="*30)
        else:
            print("No pages loaded. Aborting PageRank.")
            
    except Exception as e:
        print(f"An error occurred: {e}")