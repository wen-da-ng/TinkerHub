// frontend/src/config/fileTypes.config.ts

export const supportedFileTypes = {
    extensions: [
      '.txt', '.py', '.js', '.ts', '.tsx', '.jsx',
      '.html', '.css', '.scss', '.sass', '.less',
      '.c', '.cpp', '.h', '.hpp', '.cs', '.java',
      '.json', '.md', '.yaml', '.yml', '.xml',
      '.sh', '.bash', '.zsh', '.fish',
      '.sql', '.prisma', '.graphql', '.env',
      '.conf', '.config', '.ini', '.toml',
      '.vue', '.svelte', '.astro',
      '.rs', '.go', '.rb', '.php'
    ],
    
    languageMap: {
      '.py': 'python',
      '.js': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.jsx': 'javascript',
      '.html': 'html',
      '.css': 'css',
      '.scss': 'scss',
      '.sass': 'sass',
      '.less': 'less',
      '.c': 'c',
      '.cpp': 'cpp',
      '.h': 'c',
      '.hpp': 'cpp',
      '.cs': 'csharp',
      '.java': 'java',
      '.json': 'json',
      '.md': 'markdown',
      '.yaml': 'yaml',
      '.yml': 'yaml',
      '.xml': 'xml',
      '.sh': 'bash',
      '.bash': 'bash',
      '.zsh': 'bash',
      '.fish': 'fish',
      '.sql': 'sql',
      '.prisma': 'prisma',
      '.graphql': 'graphql',
      '.env': 'plaintext',
      '.conf': 'plaintext',
      '.config': 'plaintext',
      '.ini': 'ini',
      '.toml': 'toml',
      '.vue': 'vue',
      '.svelte': 'svelte',
      '.astro': 'astro',
      '.rs': 'rust',
      '.go': 'go',
      '.rb': 'ruby',
      '.php': 'php'
    }
  }