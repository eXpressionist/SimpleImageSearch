import { useState } from 'react';

interface CopyableTextProps {
  text: string;
  className?: string;
}

export function CopyableText({ text, className }: CopyableTextProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await copyText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch (error) {
      console.error('Failed to copy text:', error);
    }
  };

  return (
    <button
      className={`copyable-text ${className || ''} ${copied ? 'is-copied' : ''}`}
      type="button"
      title={copied ? 'Copied' : 'Copy name'}
      onClick={handleCopy}
    >
      <span>{text}</span>
      <small>{copied ? 'Copied' : 'Copy'}</small>
    </button>
  );
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}
