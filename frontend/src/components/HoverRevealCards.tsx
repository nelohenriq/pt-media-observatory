import { useState } from 'react';
import './HoverRevealCards.css';

interface CardData {
  id: number;
  title: string;
  description: string;
  status: 'active' | 'pending' | 'completed' | 'alert';
  tags: string[];
  date: string;
  author: string;
  action: string;
  icon: string;
}

const cardData: CardData[] = [
  {
    id: 1,
    title: "Media Event Monitoring",
    description: "Track breaking news events across 50+ Portuguese media outlets in real-time with automated source classification.",
    status: "active",
    tags: ["Events", "Real-time", "NLP"],
    date: "Today",
    author: "System",
    action: "View Events",
    icon: "📡"
  },
  {
    id: 2,
    title: "Publication Tracker",
    description: "Monitor where your press releases and drafts are published across outlets with status tracking and URL verification.",
    status: "active",
    tags: ["Publications", "Tracking", "Outlets"],
    date: "Today",
    author: "System",
    action: "Track Publications",
    icon: "📰"
  },
  {
    id: 3,
    title: "Risk Analysis Engine",
    description: "AI-powered risk scoring for draft content — detects confidential information, source concentration, and compliance issues.",
    status: "alert",
    tags: ["Risk", "AI", "Compliance"],
    date: "Today",
    author: "LLM Service",
    action: "Review Risks",
    icon: "⚠️"
  },
  {
    id: 4,
    title: "Coverage Analyzer",
    description: "Analyze media coverage patterns, outlet reach, and topic distribution across your press portfolio with interactive dashboards.",
    status: "pending",
    tags: ["Analytics", "Coverage", "Reports"],
    date: "Today",
    author: "Analytics",
    action: "View Analytics",
    icon: "📊"
  }
];

export default function HoverRevealCards() {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);

  const statusColors = {
    active: 'bg-green-500/20 text-green-400 border-green-500/30',
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    alert: 'bg-red-500/20 text-red-400 border-red-500/30'
  };

  return (
    <div className="hover-cards-container">
      <h1>PT Media Observatory</h1>
      <p className="subtitle">Monitor, analyze, and manage your media presence</p>

      <div className="cards-grid">
        {cardData.map((card) => (
          <div
            key={card.id}
            className="card"
            onMouseEnter={() => setHoveredCard(card.id)}
            onMouseLeave={() => setHoveredCard(null)}
          >
            <div className="card__image">
              <div className="card__icon">{card.icon}</div>
            </div>
            <div className="card__content">
              <div className="card__status-row">
                <span className={`card__status ${statusColors[card.status]}`}>
                  {card.status.charAt(0).toUpperCase() + card.status.slice(1)}
                </span>
              </div>
              <h3>{card.title}</h3>
              <p className="card__description">{card.description}</p>
              <div className="card__details">
                {card.tags.map((tag, index) => (
                  <span key={index} className="card__tag">{tag}</span>
                ))}
              </div>
              <div className="card__meta">
                <span className="card__date">{card.date}</span>
                <span className="card__author">{card.author}</span>
              </div>
            </div>
            <div className={`card__overlay ${hoveredCard === card.id ? 'visible' : ''}`}>
              <button className="card__action">{card.action}</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}