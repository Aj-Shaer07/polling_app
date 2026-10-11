import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { X, Copy, Check, ExternalLink } from 'lucide-react';

interface QRModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionTitle: string;
  joinCode: string;
}

export const QRModal: React.FC<QRModalProps> = ({ isOpen, onClose, sessionTitle, joinCode }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const joinUrl = `${window.location.origin}/student?code=${joinCode}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(joinUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center">
          <span className="inline-block px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full uppercase tracking-wider mb-2">
            Classroom Join Portal
          </span>
          <h3 className="text-xl font-bold text-slate-900">{sessionTitle}</h3>
          <p className="text-sm text-slate-500 mt-1">
            Scan with your phone or visit the student URL
          </p>

          <div className="my-6 p-4 bg-slate-50 rounded-2xl flex items-center justify-center border border-slate-200 shadow-inner">
            <QRCodeSVG
              value={joinUrl}
              size={220}
              level="H"
              includeMargin={true}
              className="rounded-lg shadow-sm"
            />
          </div>

          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Session Code
            </div>
            <div className="text-4xl font-extrabold text-indigo-600 tracking-widest my-1 font-mono">
              {joinCode}
            </div>
          </div>

          <div className="flex items-center gap-2 p-2.5 bg-slate-100 rounded-xl text-xs text-slate-700">
            <span className="truncate flex-1 font-mono text-left">{joinUrl}</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
