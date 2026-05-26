import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// KINGDOM CHESS — React Frontend
// Connects to Flask server (kingdom_server.py) on http://localhost:5000
// 10×10 board | All 12 piece types | Easy / Medium / Hard AI
// ─────────────────────────────────────────────────────────────────────────────

const API = "http://localhost:5000";

const FILES = ["a","b","c","d","e","f","g","h","i","j"];
const RANKS = [10,9,8,7,6,5,4,3,2,1];

const PIECE_UNICODE = {
  WK:"♔", WQ:"♕", WR:"♖", WB:"♗", WN:"♘", WP:"♙",
  WPS:"⚜", WPR:"⚡", WD:"🛡", WDR:"🐉", WS:"⬡", WW:"✦",
  BK:"♚", BQ:"♛", BR:"♜", BB:"♝", BN:"♞", BP:"♟",
  BPS:"⚜", BPR:"⚡", BD:"🛡", BDR:"🐉", BS:"⬡", BW:"✦",
};

const PIECE_LABEL = {
  K:"King", Q:"Queen", R:"Rook", B:"Bishop", N:"Knight", P:"Pawn",
  PS:"Princess", PR:"Prince", D:"Duke", DR:"Dragon", S:"Subject", W:"Wizard",
};

const COLOR_NAME = { W:"White", B:"Black" };

// Inline styles — no Tailwind dependency, fully self-contained
const S = {
  root: {
    minHeight:"100vh",
    background:"#0d0a06",
    backgroundImage:`
      radial-gradient(ellipse at 20% 20%, #1a0f00 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, #0a1a0a 0%, transparent 50%)
    `,
    display:"flex",
    flexDirection:"column",
    alignItems:"center",
    justifyContent:"flex-start",
    fontFamily:"'Cinzel', 'Georgia', serif",
    color:"#d4af6a",
    padding:"20px 10px 40px",
    userSelect:"none",
  },
  title: {
    fontSize:"clamp(1.4rem,4vw,2.4rem)",
    letterSpacing:"0.18em",
    textTransform:"uppercase",
    color:"#e8c97a",
    textShadow:"0 0 30px #c8962080, 0 2px 4px #000",
    margin:"0 0 4px",
    fontWeight:700,
  },
  subtitle: {
    fontSize:"0.78rem",
    letterSpacing:"0.3em",
    color:"#8a7040",
    marginBottom:"18px",
    textTransform:"uppercase",
  },
  layout: {
    display:"flex",
    gap:"24px",
    alignItems:"flex-start",
    flexWrap:"wrap",
    justifyContent:"center",
    width:"100%",
    maxWidth:"1100px",
  },
  boardWrap: {
    position:"relative",
    border:"2px solid #5a3d10",
    boxShadow:"0 0 60px #c8960030, 0 8px 32px #000a",
    borderRadius:"4px",
    background:"#1a0f00",
  },
  coordRow: {
    display:"flex",
    paddingLeft:"28px",
  },
  coordFile: {
    width:"52px",
    textAlign:"center",
    fontSize:"0.65rem",
    color:"#6a5030",
    letterSpacing:"0.1em",
    fontFamily:"'Cinzel', serif",
  },
  boardRow: {
    display:"flex",
    alignItems:"center",
  },
  coordRank: {
    width:"28px",
    textAlign:"right",
    paddingRight:"6px",
    fontSize:"0.65rem",
    color:"#6a5030",
    fontFamily:"'Cinzel', serif",
  },
  square: (light, selected, legal, lastMove) => ({
    width:"52px",
    height:"52px",
    display:"flex",
    alignItems:"center",
    justifyContent:"center",
    cursor:"pointer",
    position:"relative",
    background: selected
      ? "#c8961060"
      : lastMove
      ? "#8a6a2040"
      : legal
      ? "#3a6a2050"
      : light
      ? "#2a1e0e"
      : "#1a1008",
    border: selected
      ? "1.5px solid #c89620"
      : legal
      ? "1.5px solid #3a8a3080"
      : "1px solid #2a1a08",
    transition:"background 0.15s",
    boxSizing:"border-box",
    "&:hover": { background:"#c8962030" },
  }),
  piece: (color, draggable) => ({
    fontSize:"1.7rem",
    lineHeight:1,
    filter: color==="W"
      ? "drop-shadow(0 1px 3px #000) brightness(1.2)"
      : "drop-shadow(0 1px 3px #000) brightness(0.85)",
    cursor: draggable ? "grab" : "default",
    transition:"transform 0.1s",
    zIndex:2,
  }),
  legalDot: {
    position:"absolute",
    width:"14px",
    height:"14px",
    borderRadius:"50%",
    background:"#3a8a3060",
    border:"1.5px solid #4aaa4090",
    zIndex:1,
  },
  panel: {
    display:"flex",
    flexDirection:"column",
    gap:"14px",
    minWidth:"200px",
    maxWidth:"240px",
  },
  card: {
    background:"#150e04",
    border:"1px solid #3a2510",
    borderRadius:"4px",
    padding:"14px",
  },
  cardTitle: {
    fontSize:"0.65rem",
    letterSpacing:"0.3em",
    color:"#6a5030",
    textTransform:"uppercase",
    marginBottom:"10px",
    borderBottom:"1px solid #2a1a08",
    paddingBottom:"6px",
  },
  btn: (active, variant) => ({
    padding:"8px 12px",
    border: active ? "1px solid #c89620" : "1px solid #3a2510",
    background: active ? "#c8962020" : "transparent",
    color: active ? "#e8c97a" : "#8a7040",
    borderRadius:"3px",
    cursor:"pointer",
    fontSize:"0.75rem",
    letterSpacing:"0.15em",
    fontFamily:"'Cinzel', serif",
    textTransform:"uppercase",
    transition:"all 0.15s",
    width:"100%",
    marginBottom:"4px",
  }),
  statusBadge: (type) => ({
    display:"inline-block",
    padding:"4px 10px",
    borderRadius:"3px",
    fontSize:"0.7rem",
    letterSpacing:"0.15em",
    textTransform:"uppercase",
    background: type==="check"
      ? "#8a200020"
      : type==="turn"
      ? "#2a3a1a"
      : "#0a1a0a",
    border: type==="check"
      ? "1px solid #8a2000"
      : type==="turn"
      ? "1px solid #3a6a2060"
      : "1px solid #1a3a1a",
    color: type==="check"
      ? "#e06040"
      : "#a0c070",
    width:"100%",
    textAlign:"center",
    boxSizing:"border-box",
  }),
  moveList: {
    maxHeight:"220px",
    overflowY:"auto",
    fontSize:"0.7rem",
    lineHeight:1.8,
    color:"#8a7040",
    fontFamily:"'Courier New', monospace",
  },
  capturedRow: {
    display:"flex",
    flexWrap:"wrap",
    gap:"2px",
    fontSize:"1.1rem",
    minHeight:"24px",
  },
  select: {
    background:"#150e04",
    border:"1px solid #3a2510",
    color:"#d4af6a",
    padding:"6px 8px",
    borderRadius:"3px",
    fontSize:"0.75rem",
    fontFamily:"'Cinzel', serif",
    width:"100%",
    cursor:"pointer",
  },
  promoOverlay: {
    position:"fixed",
    inset:0,
    background:"#000000b0",
    display:"flex",
    alignItems:"center",
    justifyContent:"center",
    zIndex:100,
  },
  promoBox: {
    background:"#150e04",
    border:"2px solid #c89620",
    borderRadius:"6px",
    padding:"24px",
    display:"flex",
    flexDirection:"column",
    alignItems:"center",
    gap:"14px",
  },
  promoTitle: {
    color:"#e8c97a",
    fontSize:"0.8rem",
    letterSpacing:"0.25em",
    textTransform:"uppercase",
  },
  promoRow: {
    display:"flex",
    gap:"10px",
  },
  promoBtn: {
    width:"52px",
    height:"52px",
    background:"#2a1e0e",
    border:"1px solid #5a3d10",
    borderRadius:"4px",
    cursor:"pointer",
    display:"flex",
    flexDirection:"column",
    alignItems:"center",
    justifyContent:"center",
    color:"#d4af6a",
    fontSize:"1.5rem",
    fontFamily:"'Cinzel', serif",
    transition:"border-color 0.15s",
  },
  spinner: {
    display:"inline-block",
    width:"16px",
    height:"16px",
    border:"2px solid #3a2510",
    borderTop:"2px solid #c89620",
    borderRadius:"50%",
    animation:"spin 0.8s linear infinite",
  },
};

// ─────────────────────────────────────────────────────────────────────────────

function squareKey(f, r) {
  return `${FILES[f]}${r}`;
}

function parseBoard(boardObj) {
  // boardObj: { "e1": "WK", "a1": "WR", ... }
  const grid = {};
  if (boardObj) {
    Object.entries(boardObj).forEach(([sq, code]) => { grid[sq] = code; });
  }
  return grid;
}

function pieceColor(code) {
  return code[0]; // "W" or "B"
}

function pieceKind(code) {
  return code.slice(1); // "K", "PS", etc.
}

// ─────────────────────────────────────────────────────────────────────────────

export default function KingdomChess() {
  const [gameState, setGameState] = useState(null);   // from server
  const [board, setBoard] = useState({});
  const [selected, setSelected] = useState(null);     // square key
  const [legalDsts, setLegalDsts] = useState([]);     // legal dest square keys
  const [legalMoves, setLegalMoves] = useState([]);   // full move objects
  const [lastMove, setLastMove] = useState(null);     // {src, dst}
  const [moveHistory, setMoveHistory] = useState([]);
  const [captured, setCaptured] = useState({ W:[], B:[] });
  const [level, setLevel] = useState("medium");
  const [playerColor, setPlayerColor] = useState("W");
  const [thinking, setThinking] = useState(false);
  const [message, setMessage] = useState("Welcome to Kingdom Chess");
  const [gameOver, setGameOver] = useState(false);
  const [promoState, setPromoState] = useState(null); // { src, dst, choices }
  const [dukeStatus, setDukeStatus] = useState({ W:true, B:true });
  const [dragonStatus, setDragonStatus] = useState({ W:true, B:true });
  const [serverOk, setServerOk] = useState(null);

  // Check server connectivity
  useEffect(() => {
    fetch(`${API}/ping`)
      .then(r => r.ok ? setServerOk(true) : setServerOk(false))
      .catch(() => setServerOk(false));
  }, []);

  const initGame = useCallback(async () => {
    try {
      const r = await fetch(`${API}/new_game`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ level, player_color: playerColor }),
      });
      const data = await r.json();
      setGameState(data);
      setBoard(parseBoard(data.board));
      setSelected(null);
      setLegalDsts([]);
      setLegalMoves([]);
      setLastMove(null);
      setMoveHistory([]);
      setCaptured({ W:[], B:[] });
      setGameOver(false);
      setMessage(`Game started — ${data.turn === "W" ? "White" : "Black"} to move`);
      setDukeStatus({ W: data.duke_W, B: data.duke_B });
      setDragonStatus({ W: data.dragon_W, B: data.dragon_B });
    } catch {
      setMessage("⚠ Cannot connect to server. Start kingdom_server.py first.");
    }
  }, [level, playerColor]);

  useEffect(() => { initGame(); }, []);

  const fetchLegalMoves = async (sq) => {
    if (!gameState) return;
    try {
      const r = await fetch(`${API}/legal_moves`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game_id: gameState.game_id, square: sq }),
      });
      const data = await r.json();
      setLegalMoves(data.moves || []);
      setLegalDsts((data.moves || []).map(m => m.dst));
    } catch { setLegalMoves([]); setLegalDsts([]); }
  };

  const handleSquareClick = async (sq) => {
    if (gameOver || thinking || !gameState) return;
    if (gameState.turn !== playerColor) return;

    const pc = board[sq];

    // Deselect
    if (selected === sq) {
      setSelected(null); setLegalDsts([]); setLegalMoves([]);
      return;
    }

    // Select own piece
    if (pc && pieceColor(pc) === playerColor) {
      setSelected(sq);
      await fetchLegalMoves(sq);
      return;
    }

    // Attempt move
    if (selected && legalDsts.includes(sq)) {
      const movesForDst = legalMoves.filter(m => m.dst === sq);

      // Promotion choice needed?
      if (movesForDst.length > 1 && movesForDst[0].special === "PROMO_PAWN") {
        setPromoState({ src: selected, dst: sq, choices: movesForDst });
        return;
      }

      await executeMove(movesForDst[0]);
      return;
    }

    setSelected(null); setLegalDsts([]); setLegalMoves([]);
  };

  const executeMove = async (moveObj) => {
    if (!moveObj) return;
    setSelected(null); setLegalDsts([]); setLegalMoves([]);
    setThinking(true);

    try {
      const r = await fetch(`${API}/make_move`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game_id: gameState.game_id, move: moveObj.notation }),
      });
      const data = await r.json();

      if (data.error) { setMessage(`Error: ${data.error}`); setThinking(false); return; }

      setGameState(data);
      setBoard(parseBoard(data.board));
      setLastMove({ src: moveObj.src, dst: moveObj.dst });
      setDukeStatus({ W: data.duke_W, B: data.duke_B });
      setDragonStatus({ W: data.dragon_W, B: data.dragon_B });

      // Update history
      setMoveHistory(h => [...h, moveObj.notation]);

      // Update captured
      if (data.captured) {
        setCaptured(prev => ({
          ...prev,
          [playerColor]: [...prev[playerColor], data.captured],
        }));
      }

      if (data.game_over) {
        setMessage(data.result || "Game over");
        setGameOver(true);
        setThinking(false);
        return;
      }

      setMessage(data.in_check ? "⚔ Check!" : `${data.turn === "W" ? "White" : "Black"} to move`);

      // AI moves if it's AI's turn
      if (data.turn !== playerColor) {
        await triggerAI(data.game_id);
      }
    } catch (e) {
      setMessage("Server error");
    }
    setThinking(false);
  };

  const triggerAI = async (game_id) => {
    setThinking(true);
    setMessage("AI is thinking…");
    try {
      const r = await fetch(`${API}/ai_move`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game_id: game_id || gameState.game_id }),
      });
      const data = await r.json();

      if (data.error) { setMessage(`AI error: ${data.error}`); setThinking(false); return; }

      setGameState(data);
      setBoard(parseBoard(data.board));
      if (data.ai_move) setLastMove({ src: data.ai_move.src, dst: data.ai_move.dst });
      setDukeStatus({ W: data.duke_W, B: data.duke_B });
      setDragonStatus({ W: data.dragon_W, B: data.dragon_B });
      setMoveHistory(h => [...h, data.ai_move?.notation || "?"]);

      if (data.captured) {
        const aiColor = playerColor === "W" ? "B" : "W";
        setCaptured(prev => ({
          ...prev,
          [aiColor]: [...prev[aiColor], data.captured],
        }));
      }

      if (data.game_over) {
        setMessage(data.result || "Game over");
        setGameOver(true);
      } else {
        setMessage(data.in_check ? "⚔ Check!" : `Your turn (${playerColor === "W" ? "White" : "Black"})`);
      }
    } catch { setMessage("AI error"); }
    setThinking(false);
  };

  const handlePromoChoice = async (moveObj) => {
    setPromoState(null);
    await executeMove(moveObj);
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (serverOk === false) {
    return (
      <div style={S.root}>
        <h1 style={S.title}>Kingdom Chess</h1>
        <div style={{ ...S.card, maxWidth:"480px", marginTop:"40px", textAlign:"center", lineHeight:1.8 }}>
          <div style={{ fontSize:"2rem", marginBottom:"12px" }}>⚠</div>
          <div style={{ color:"#e06040", marginBottom:"12px", fontSize:"0.9rem" }}>
            Server not running
          </div>
          <div style={{ color:"#8a7040", fontSize:"0.8rem" }}>
            Start the Flask server first:<br/>
            <code style={{ color:"#c89620", fontSize:"0.85rem" }}>python kingdom_server.py</code><br/><br/>
            Then refresh this page.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={S.root}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:#0d0a06; }
        ::-webkit-scrollbar-thumb { background:#3a2510; border-radius:2px; }
      `}</style>

      <h1 style={S.title}>Kingdom Chess</h1>
      <div style={S.subtitle}>A Variant by Josef Laspina · MotoHov Industries</div>

      <div style={S.layout}>

        {/* ── Board ── */}
        <div>
          {/* File coordinates top */}
          <div style={S.coordRow}>
            {FILES.map(f => <div key={f} style={S.coordFile}>{f}</div>)}
          </div>

          <div style={S.boardWrap}>
            {RANKS.map((rank) => (
              <div key={rank} style={S.boardRow}>
                <div style={S.coordRank}>{rank}</div>
                {FILES.map((file, fi) => {
                  const sqKey = `${file}${rank}`;
                  const light = (fi + rank) % 2 === 0;
                  const isSelected = selected === sqKey;
                  const isLegal = legalDsts.includes(sqKey);
                  const isLastMove = lastMove && (lastMove.src === sqKey || lastMove.dst === sqKey);
                  const pc = board[sqKey];

                  return (
                    <div
                      key={sqKey}
                      style={S.square(light, isSelected, isLegal, isLastMove)}
                      onClick={() => handleSquareClick(sqKey)}
                    >
                      {isLegal && !pc && <div style={S.legalDot} />}
                      {pc && (
                        <span
                          style={S.piece(pieceColor(pc), pieceColor(pc) === playerColor)}
                          title={`${COLOR_NAME[pieceColor(pc)]} ${PIECE_LABEL[pieceKind(pc)]}`}
                        >
                          {PIECE_UNICODE[pc] || pieceKind(pc)}
                        </span>
                      )}
                    </div>
                  );
                })}
                <div style={{ ...S.coordRank, paddingLeft:"6px", paddingRight:0 }}>{rank}</div>
              </div>
            ))}
          </div>

          {/* File coordinates bottom */}
          <div style={S.coordRow}>
            {FILES.map(f => <div key={f} style={S.coordFile}>{f}</div>)}
          </div>
        </div>

        {/* ── Side Panel ── */}
        <div style={S.panel}>

          {/* Status */}
          <div style={S.card}>
            <div style={S.cardTitle}>Status</div>
            <div style={{ ...S.statusBadge(gameOver ? "over" : "turn"), marginBottom:"8px", animation: thinking ? "pulse 1s infinite" : "none" }}>
              {thinking ? <><span style={S.spinner}/>{" Thinking…"}</> : message}
            </div>
            {gameState && (
              <div style={{ fontSize:"0.68rem", color:"#6a5030", marginTop:"6px" }}>
                Move {gameState.fullmove} · {gameState.turn === "W" ? "White" : "Black"} to move
              </div>
            )}
          </div>

          {/* Piece Legend */}
          <div style={S.card}>
            <div style={S.cardTitle}>Kingdom Status</div>
            {["W","B"].map(c => (
              <div key={c} style={{ marginBottom:"8px" }}>
                <div style={{ fontSize:"0.68rem", color:"#8a7040", marginBottom:"4px" }}>
                  {COLOR_NAME[c]}
                </div>
                <div style={{ fontSize:"0.7rem", color: dukeStatus[c] ? "#6a9a40" : "#e06040" }}>
                  Duke: {dukeStatus[c] ? "◆ Alive" : "✕ Captured"}
                </div>
                <div style={{ fontSize:"0.7rem", color: dragonStatus[c] ? "#6a9a40" : "#e06040", marginTop:"2px" }}>
                  Dragon: {dragonStatus[c] ? "◆ Alive" : "✕ Captured"}
                </div>
              </div>
            ))}
          </div>

          {/* Controls */}
          <div style={S.card}>
            <div style={S.cardTitle}>Settings</div>
            <div style={{ fontSize:"0.68rem", color:"#6a5030", marginBottom:"4px" }}>Difficulty</div>
            <select style={S.select} value={level} onChange={e => setLevel(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
            <div style={{ fontSize:"0.68rem", color:"#6a5030", margin:"8px 0 4px" }}>Play as</div>
            <select style={S.select} value={playerColor} onChange={e => setPlayerColor(e.target.value)}>
              <option value="W">White</option>
              <option value="B">Black</option>
            </select>
            <button style={{ ...S.btn(false), marginTop:"12px" }} onClick={initGame}>
              New Game
            </button>
            {!gameOver && gameState?.turn !== playerColor && !thinking && (
              <button style={S.btn(true)} onClick={() => triggerAI()}>
                AI Move
              </button>
            )}
          </div>

          {/* Captured pieces */}
          <div style={S.card}>
            <div style={S.cardTitle}>Captured</div>
            <div style={{ fontSize:"0.68rem", color:"#6a5030", marginBottom:"4px" }}>By White</div>
            <div style={S.capturedRow}>
              {captured.W.map((c,i) => <span key={i} title={c}>{PIECE_UNICODE["B"+c] || c}</span>)}
            </div>
            <div style={{ fontSize:"0.68rem", color:"#6a5030", margin:"8px 0 4px" }}>By Black</div>
            <div style={S.capturedRow}>
              {captured.B.map((c,i) => <span key={i} title={c}>{PIECE_UNICODE["W"+c] || c}</span>)}
            </div>
          </div>

          {/* Move history */}
          <div style={S.card}>
            <div style={S.cardTitle}>Move History</div>
            <div style={S.moveList}>
              {moveHistory.map((m,i) => (
                <span key={i}>
                  {i % 2 === 0 && <span style={{ color:"#5a4020" }}>{Math.floor(i/2)+1}. </span>}
                  <span>{m} </span>
                </span>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Piece Legend */}
      <div style={{ ...S.card, marginTop:"20px", maxWidth:"700px", width:"100%" }}>
        <div style={S.cardTitle}>Piece Reference</div>
        <div style={{ display:"flex", flexWrap:"wrap", gap:"10px" }}>
          {Object.entries(PIECE_LABEL).map(([k,v]) => (
            <div key={k} style={{ fontSize:"0.7rem", color:"#8a7040", display:"flex", alignItems:"center", gap:"4px" }}>
              <span style={{ fontSize:"1.2rem" }}>{PIECE_UNICODE["W"+k]}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Promotion Modal */}
      {promoState && (
        <div style={S.promoOverlay}>
          <div style={S.promoBox}>
            <div style={S.promoTitle}>Choose Promotion Piece</div>
            <div style={S.promoRow}>
              {promoState.choices.map((m,i) => (
                <button key={i} style={S.promoBtn} onClick={() => handlePromoChoice(m)}
                  title={PIECE_LABEL[m.promo_to] || m.promo_to}>
                  <span>{PIECE_UNICODE[playerColor + m.promo_to] || m.promo_to}</span>
                  <span style={{ fontSize:"0.45rem", marginTop:"2px" }}>{m.promo_to}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
