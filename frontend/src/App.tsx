import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Activity, CheckCircle2, Clock, PlayCircle, Loader2 } from 'lucide-react';
import { getWebSocketUrl, shouldIgnoreSocketClose } from './ws';

interface ChatMessage {
  id: string;
  sender: 'user' | 'system' | 'orchestrator';
  text: string;
  timestamp: Date;
}

interface MatchData {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: 'pending' | 'analyzing' | 'trading' | 'done' | 'error';
  predictions?: {
    home_win?: number;
    draw?: number;
    away_win?: number;
  };
  ev?: number;
  recommendation?: string;
  error?: string;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [matches, setMatches] = useState<Record<string, MatchData>>({});
  const [globalStatus, setGlobalStatus] = useState<string>('Idle');
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const addMessage = useCallback((sender: 'user' | 'system' | 'orchestrator', text: string) => {
    setMessages(prev => [...prev, {
      id: Math.random().toString(36).substring(7),
      sender,
      text,
      timestamp: new Date()
    }]);
  }, []);

  const handleServerEvent = useCallback((data: unknown) => {
    const event = data as { type?: string; payload?: Record<string, unknown> };
    const type = event.type;
    const payload = event.payload ?? {};

    switch (type) {
      case 'chat_chunk':
        addMessage('orchestrator', String(payload.text ?? ''));
        break;
      
      case 'pipeline_start':
        setGlobalStatus('Pipeline Running...');
        addMessage('orchestrator', String(payload.message ?? 'Starting analysis pipeline...'));
        setMatches({});
        break;

      case 'matches_found': {
        addMessage('orchestrator', `Found ${String(payload.total ?? 0)} matches to analyze.`);
        const newMatches: Record<string, MatchData> = {};
        const matchList = payload.matches;
        if (Array.isArray(matchList)) {
          matchList.forEach((item) => {
            const match = item as Partial<MatchData>;
            if (!match.match_id) return;
            newMatches[match.match_id] = {
              match_id: match.match_id,
              home_team: match.home_team ?? '',
              away_team: match.away_team ?? '',
              kickoff_time: match.kickoff_time ?? '',
              status: 'pending'
            };
          });
        }
        setMatches(prev => ({ ...prev, ...newMatches }));
        break;
      }

      case 'match_step_start':
        setMatches(prev => {
          const matchId = String(payload.match_id ?? '');
          if (!prev[matchId]) return prev;
          return {
            ...prev,
            [matchId]: {
              ...prev[matchId],
              status: payload.step === 'analyst' ? 'analyzing' : 
                      payload.step === 'trader' ? 'trading' : 'analyzing'
            }
          };
        });
        break;

      case 'match_result_ready':
        setMatches(prev => {
          const matchId = String(payload.match_id ?? '');
          if (!prev[matchId]) return prev;
          return {
            ...prev,
            [matchId]: {
              ...prev[matchId],
              status: 'done',
              predictions: payload.predictions as MatchData['predictions'],
              ev: typeof payload.ev === 'number' ? payload.ev : undefined,
              recommendation: typeof payload.recommendation === 'string' ? payload.recommendation : undefined
            }
          };
        });
        break;
        
      case 'match_step_error':
        setMatches(prev => {
          const matchId = String(payload.match_id ?? '');
          if (!prev[matchId]) return prev;
          return {
            ...prev,
            [matchId]: {
              ...prev[matchId],
              status: 'error',
              error: String(payload.message ?? 'Unknown error occurred')
            }
          };
        });
        break;

      case 'pipeline_complete':
        setGlobalStatus('Pipeline Completed');
        addMessage('orchestrator', String(payload.message ?? 'All matches analyzed.'));
        break;

      default:
        console.log('Unknown event type:', type, payload);
    }
  }, [addMessage]);

  useEffect(() => {
    // Scroll to bottom of chat
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const wsUrl = getWebSocketUrl();

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (wsRef.current !== ws) return;
      setIsConnected(true);
      addMessage('system', 'Connected to Goalcast Orchestrator.');
      setGlobalStatus('Ready');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.onclose = () => {
      if (shouldIgnoreSocketClose(ws, wsRef.current)) return;
      setIsConnected(false);
      addMessage('system', 'Connection lost. Please refresh.');
      setGlobalStatus('Disconnected');
    };

    return () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      ws.close();
    };
  }, [addMessage, handleServerEvent]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !wsRef.current || !isConnected) return;

    addMessage('user', inputValue);
    wsRef.current.send(inputValue);
    setInputValue('');
  };

  const renderMatchStatusIcon = (status: string) => {
    switch(status) {
      case 'pending': return <Clock className="w-5 h-5 text-gray-500" />;
      case 'analyzing': return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'trading': return <PlayCircle className="w-5 h-5 text-yellow-400 animate-pulse" />;
      case 'done': return <CheckCircle2 className="w-5 h-5 text-brand-green" />;
      case 'error': return <Activity className="w-5 h-5 text-brand-red" />;
      default: return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const matchesList = Object.values(matches);

  return (
    <div className="flex h-screen bg-brand-dark text-brand-light overflow-hidden font-sans">
      
      {/* LEFT PANEL: Chat Interface */}
      <div className="w-1/3 border-r border-brand-gray flex flex-col bg-[#0d0d0d]">
        <div className="p-4 border-b border-brand-gray flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <Activity className="text-brand-green w-6 h-6" />
              Goalcast
            </h1>
            <p className="text-xs text-gray-400 mt-1">Orchestrator Terminal</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-brand-green animate-pulse' : 'bg-brand-red'}`}></div>
            <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
              {isConnected ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] rounded-lg p-3 text-sm ${
                msg.sender === 'user' 
                  ? 'bg-brand-green text-brand-dark rounded-tr-none' 
                  : msg.sender === 'system'
                    ? 'bg-brand-gray text-gray-400 text-xs italic'
                    : 'bg-brand-accent text-brand-light rounded-tl-none border border-brand-gray'
              }`}>
                {msg.text}
              </div>
              <span className="text-[10px] text-gray-500 mt-1 px-1">
                {msg.timestamp.toLocaleTimeString()}
              </span>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div className="p-4 bg-brand-dark border-t border-brand-gray">
          <form onSubmit={handleSend} className="relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="e.g., 分析今天英超和德甲..."
              disabled={!isConnected}
              className="w-full bg-brand-accent text-white rounded-lg pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand-green disabled:opacity-50 transition-all border border-transparent focus:border-brand-green/30"
            />
            <button 
              type="submit" 
              disabled={!isConnected || !inputValue.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-brand-green text-brand-dark rounded-md hover:bg-[#00e68d] disabled:opacity-50 disabled:hover:bg-brand-green transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT PANEL: Pipeline Monitor */}
      <div className="flex-1 flex flex-col bg-brand-dark">
        {/* Header */}
        <div className="p-6 border-b border-brand-gray flex justify-between items-center bg-[#0a0a0a]">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Pipeline Monitor</h2>
            <p className="text-gray-400 text-sm mt-1">Real-time analysis tracking & results</p>
          </div>
          <div className="px-4 py-2 bg-brand-accent rounded-lg border border-brand-gray flex items-center gap-3">
            <span className="text-sm text-gray-400">Status:</span>
            <span className={`text-sm font-bold ${globalStatus.includes('Running') ? 'text-blue-400' : 'text-brand-green'}`}>
              {globalStatus}
            </span>
          </div>
        </div>

        {/* Match Cards Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {matchesList.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500">
              <Activity className="w-16 h-16 mb-4 opacity-20" />
              <p>No matches in current pipeline.</p>
              <p className="text-sm mt-2">Send a request to orchestrator to start.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
              {matchesList.map((match) => (
                <div key={match.match_id} className="bg-brand-accent rounded-xl border border-brand-gray overflow-hidden hover:border-brand-gray/80 transition-colors shadow-lg">
                  
                  {/* Card Header */}
                  <div className="p-4 border-b border-brand-gray/50 flex justify-between items-start bg-[#161616]">
                    <div>
                      <div className="text-xs text-brand-green font-mono mb-1">{match.match_id.substring(0, 8)}</div>
                      <div className="font-bold text-lg text-white">{match.home_team}</div>
                      <div className="text-sm text-gray-400">vs {match.away_team}</div>
                    </div>
                    <div className="flex flex-col items-end">
                      {renderMatchStatusIcon(match.status)}
                      <span className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mt-2">
                        {match.status}
                      </span>
                    </div>
                  </div>

                  {/* Card Body */}
                  <div className="p-4 min-h-[120px] flex flex-col justify-center">
                    {match.status === 'done' ? (
                      <div className="space-y-4 animate-in fade-in">
                        {/* Predictions Bar */}
                        {match.predictions && (
                          <div className="flex h-2 rounded-full overflow-hidden w-full bg-brand-dark">
                            <div style={{ width: `${(match.predictions.home_win || 0) * 100}%` }} className="bg-brand-green"></div>
                            <div style={{ width: `${(match.predictions.draw || 0) * 100}%` }} className="bg-gray-500"></div>
                            <div style={{ width: `${(match.predictions.away_win || 0) * 100}%` }} className="bg-blue-500"></div>
                          </div>
                        )}
                        
                        {/* Results Data */}
                        <div className="flex justify-between items-end">
                          <div>
                            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Recommendation</div>
                            <div className="font-bold text-white bg-brand-dark px-3 py-1.5 rounded inline-block border border-brand-gray">
                              {match.recommendation || 'No Bet'}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Edge (EV)</div>
                            <div className={`font-mono text-xl font-bold ${
                              (match.ev || 0) > 1.05 ? 'text-brand-green' : 
                              (match.ev || 0) > 1.0 ? 'text-yellow-400' : 'text-brand-red'
                            }`}>
                              {match.ev ? match.ev.toFixed(3) : '-'}
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : match.status === 'error' ? (
                      <div className="text-brand-red text-sm flex items-start gap-2">
                        <Activity className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{match.error}</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <div className="w-full bg-brand-dark h-1.5 rounded-full overflow-hidden">
                          <div className="bg-brand-green h-full w-1/3 animate-[slide_1.5s_ease-in-out_infinite]"></div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default App;
