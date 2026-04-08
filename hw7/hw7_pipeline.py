import argparse
from collections import Counter
import re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam.io import fileio

class ExtractFeaturesFn(beam.DoFn):
    """Parses HTML files to extract outgoing links, incoming links, and bigrams."""
    def process(self, readable_file):
        # 1. Get the filename
        filename = readable_file.metadata.path.split('/')[-1]
        
        # 2. Read the content
        content = readable_file.read_utf8()
        
        # Extract Links (Looking for href="...")
        links = re.findall(r'href=["\']([^"\'>]+)["\']', content)
        
        # Branch A: Outgoing Links (Yield the current file and its total link count)
        yield beam.pvalue.TaggedOutput('outgoing', (filename, len(links)))
        
        # Branch B: Incoming Links (Yield each link found with a count of 1)
        for link in links:
            target_file = link.split('/')[-1] # Clean up paths if any exist
            yield beam.pvalue.TaggedOutput('incoming', (target_file, 1))
            
        # Extract Bigrams
        # Strip HTML tags first so we only get visible text
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        words = re.findall(r'[a-z]+', clean_text.lower())
        
        # Branch C: Bigrams (Yield consecutive word pairs)
        bigram_counts = Counter(
            f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)
        )
        for bigram, count in bigram_counts.items():
            yield beam.pvalue.TaggedOutput('bigrams', (bigram, count))

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', dest='input', required=True, help='Input file pattern (e.g., gs://bucket/*.html)')
    parser.add_argument('--output', dest='output', required=True, help='Output prefix for results')
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True

    with beam.Pipeline(options=pipeline_options) as p:
        # Step 1: Match and Read Files
        parsed_data = (
            p 
            | 'Match Files' >> fileio.MatchFiles(known_args.input) # <-- Updated
            | 'Read Matches' >> fileio.ReadMatches()               # <-- Updated
            | 'Extract Features' >> beam.ParDo(ExtractFeaturesFn()).with_outputs('outgoing', 'incoming', 'bigrams')
        )

        # Step 2: Calculate Top 5 Outgoing Links
        (parsed_data.outgoing
         | 'Top 5 Outgoing' >> beam.combiners.Top.Of(5, key=lambda x: x[1])
         | 'Format Outgoing' >> beam.Map(lambda x: f"Top 5 Outgoing Links (File, Count):\n{x}")
         | 'Write Outgoing' >> beam.io.WriteToText(f"{known_args.output}-outgoing", num_shards=1))

        # Step 3: Calculate Top 5 Incoming Links
        (parsed_data.incoming
         | 'Sum Incoming' >> beam.CombinePerKey(sum)
         | 'Top 5 Incoming' >> beam.combiners.Top.Of(5, key=lambda x: x[1])
         | 'Format Incoming' >> beam.Map(lambda x: f"Top 5 Incoming Links (Target File, Count):\n{x}")
         | 'Write Incoming' >> beam.io.WriteToText(f"{known_args.output}-incoming", num_shards=1))

        # Step 4: Calculate Top 5 Bigrams
        (parsed_data.bigrams
         | 'Sum Bigrams' >> beam.CombinePerKey(sum)
         | 'Top 5 Bigrams' >> beam.combiners.Top.Of(5, key=lambda x: x[1])
         | 'Format Bigrams' >> beam.Map(lambda x: f"Top 5 Word Bigrams (Bigram, Count):\n{x}")
         | 'Write Bigrams' >> beam.io.WriteToText(f"{known_args.output}-bigrams", num_shards=1))

if __name__ == '__main__':
    run()