<script>
  import { marked } from 'marked';

  let { content = '', class: className = '' } = $props();

  // Configure marked for safe rendering
  marked.setOptions({
    breaks: true,  // Convert \n to <br>
    gfm: true      // Enable GitHub Flavored Markdown
  });

  let html = $derived(content ? marked.parse(content) : '');
</script>

<div class="markdown-content prose prose-sm max-w-none {className}">
  {@html html}
</div>

<style>
  .markdown-content :global(h1) {
    font-size: 1.5em;
    font-weight: 700;
    margin-top: 1em;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(h2) {
    font-size: 1.25em;
    font-weight: 600;
    margin-top: 1em;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(h3) {
    font-size: 1.1em;
    font-weight: 600;
    margin-top: 0.75em;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(p) {
    margin-bottom: 0.5em;
  }
  .markdown-content :global(ul), .markdown-content :global(ol) {
    margin-left: 1.5em;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(ul) {
    list-style-type: disc;
  }
  .markdown-content :global(ol) {
    list-style-type: decimal;
  }
  .markdown-content :global(li) {
    margin-bottom: 0.25em;
  }
  .markdown-content :global(strong) {
    font-weight: 600;
  }
  .markdown-content :global(em) {
    font-style: italic;
  }
  .markdown-content :global(code) {
    background-color: #f3f4f6;
    padding: 0.125em 0.25em;
    border-radius: 0.25em;
    font-family: monospace;
    font-size: 0.9em;
  }
  .markdown-content :global(pre) {
    background-color: #f3f4f6;
    padding: 0.75em;
    border-radius: 0.375em;
    overflow-x: auto;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(pre code) {
    background-color: transparent;
    padding: 0;
  }
  .markdown-content :global(blockquote) {
    border-left: 3px solid #d1d5db;
    padding-left: 1em;
    margin-left: 0;
    margin-bottom: 0.5em;
    color: #6b7280;
  }
  .markdown-content :global(hr) {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1em 0;
  }
  .markdown-content :global(table) {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 0.5em;
  }
  .markdown-content :global(th), .markdown-content :global(td) {
    border: 1px solid #e5e7eb;
    padding: 0.5em;
    text-align: left;
  }
  .markdown-content :global(th) {
    background-color: #f9fafb;
    font-weight: 600;
  }
</style>
