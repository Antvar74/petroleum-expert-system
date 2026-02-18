/**
 * DecisionTreeDiagram.tsx — Visual flowchart of the stuck pipe diagnosis path.
 */
import React from 'react';
import { motion } from 'framer-motion';

interface DiagnosisStep {
  node_id: string;
  question: string;
  answer: string;
}

interface DecisionTreeDiagramProps {
  path: DiagnosisStep[];
  currentQuestion?: { node_id: string; question: string } | null;
  result?: { mechanism: string; description: string } | null;
}

const DecisionTreeDiagram: React.FC<DecisionTreeDiagramProps> = ({
  path,
  currentQuestion,
  result,
}) => {
  const allNodes = [
    ...path.map((step) => ({
      id: step.node_id,
      text: step.question.length > 50 ? step.question.substring(0, 48) + '...' : step.question,
      answer: step.answer,
      type: 'answered' as const,
    })),
    ...(currentQuestion ? [{
      id: currentQuestion.node_id,
      text: currentQuestion.question.length > 50 ? currentQuestion.question.substring(0, 48) + '...' : currentQuestion.question,
      answer: '',
      type: 'active' as const,
    }] : []),
    ...(result ? [{
      id: 'result',
      text: result.mechanism,
      answer: '',
      type: 'result' as const,
    }] : []),
  ];

  if (allNodes.length === 0) return null;

  const nodeW = 220;
  const nodeH = 50;
  const gapY = 30;
  const svgW = nodeW + 80;
  const svgH = allNodes.length * (nodeH + gapY) + 20;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 print-chart overflow-auto" style={{ maxHeight: 500 }}>
      <h4 className="font-bold text-sm mb-4">Diagnosis Path</h4>

      <svg width={svgW} height={svgH} viewBox={`0 0 ${svgW} ${svgH}`} className="mx-auto">
        {allNodes.map((node, i) => {
          const x = (svgW - nodeW) / 2;
          const y = 10 + i * (nodeH + gapY);

          // Connector line to next node
          const connector = i < allNodes.length - 1 ? (
            <g key={`conn-${i}`}>
              <line
                x1={svgW / 2} y1={y + nodeH}
                x2={svgW / 2} y2={y + nodeH + gapY}
                stroke={node.answer === 'yes' ? '#22c55e' : node.answer === 'no' ? '#ef4444' : 'rgba(255,255,255,0.2)'}
                strokeWidth={2}
                strokeDasharray={node.type === 'active' ? '4 2' : 'none'}
              />
              {node.answer && (
                <text
                  x={svgW / 2 + 12}
                  y={y + nodeH + gapY / 2 + 3}
                  fill={node.answer === 'yes' ? '#22c55e' : '#ef4444'}
                  fontSize="9"
                  fontWeight="700"
                >
                  {node.answer.toUpperCase()}
                </text>
              )}
            </g>
          ) : null;

          // Node colors
          const bgColor = node.type === 'result'
            ? 'rgba(249,115,22,0.2)'
            : node.type === 'active'
              ? 'rgba(99,102,241,0.2)'
              : 'rgba(255,255,255,0.05)';
          const borderColor = node.type === 'result'
            ? '#f97316'
            : node.type === 'active'
              ? '#6366f1'
              : 'rgba(255,255,255,0.1)';

          return (
            <React.Fragment key={i}>
              {connector}
              <motion.g
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <rect
                  x={x} y={y} width={nodeW} height={nodeH}
                  fill={bgColor} stroke={borderColor} strokeWidth={1.5}
                  rx={10}
                />
                {node.type === 'active' && (
                  <motion.rect
                    x={x} y={y} width={nodeW} height={nodeH}
                    fill="none" stroke="#6366f1" strokeWidth={2}
                    rx={10}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                  />
                )}
                <text
                  x={x + nodeW / 2} y={y + nodeH / 2 + 4}
                  fill={node.type === 'result' ? '#f97316' : 'rgba(255,255,255,0.8)'}
                  fontSize={node.type === 'result' ? '11' : '10'}
                  fontWeight={node.type === 'result' ? '700' : '400'}
                  textAnchor="middle"
                >
                  {node.text}
                </text>
              </motion.g>
            </React.Fragment>
          );
        })}
      </svg>
    </div>
  );
};

export default DecisionTreeDiagram;
