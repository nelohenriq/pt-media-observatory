import { useState } from 'react';
import { Button, Checkbox, FormControl, Label, Card, CardHeader, CardBody, CardTitle, Dialog, DialogOverlay, DialogContent, DialogHeader, DialogTitle, DialogBody, Switch } from '@/components/ui';

type Draft = {
  id: string;
  title: string;
  content: string;
  status: 'draft' | 'approved' | 'rejected' | 'revision';
  riskScore: number;
  sourceOutlets?: string[];
};

type Props = {
  draft: Draft;
  onClose?: () => void;
};

export default function ReviewPanel({ draft, onClose }: Props) {
  const [showDraftPreview, setShowDraftPreview] = useState(true);
  const [riskWarnings, setRiskWarnings] = useState<string[]>([]);
  const [selectedOutlets, setSelectedOutlets] = useState<string[]>(draft.sourceOutlets ?? []);

  // Simulated risk detection
  useState(() => {
    const warnings: string[] = [];
    if (draft.riskScore > 70) warnings.push('High source concentration detected');
    if (draft.content.includes('confidential') && !draft.content.includes('public')) warnings.push('Potential confidential content');
    setRiskWarnings(warnings);
  }, []);

  const handleApprove = async () => {
    // TODO: call API to approve draft
    // await approveDraft(draft.id);
    setShowDraftPreview(false);
  };

  const handleReject = async () => {
    // TODO: call API to reject draft
    setShowDraftPreview(false);
  };

  const handleRequestRevision = async () => {
    // TODO: call API to request revision
    setShowDraftPreview(false);
  };

  const handleForceApprove = async () => {
    // TODO: call API to force approve draft
    setShowDraftPreview(false);
  };

  return (
    <Dialog as={DialogOverlay}>
      <Dialog as={Dialog} onClose={onClose}>
        <DialogHeader>Review Draft: {draft.title}</DialogHeader>
        <DialogBody className="p-4 space-y-4">
          {/* Risk Flags Panel */}
          <Card>
            <CardHeader>Risk Analysis</CardHeader>
            <CardBody>
              {riskWarnings.length > 0 ? (
                <ul className="space-y-2 text-sm">
                  {riskWarnings.map((warn, i) => (
                    <li key={i} className="flex items-baseline justify-between">
                      <span className="text-red-600">{warn}</span>
                      <span className="text-xs flex items-center gap-1">
                        <span className="rounded-full px-1 py-0.5 bg-red-100 text-red-600 text-xs">⚠</span>
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-green-600">No critical risks detected.</p>
              )}

              <Switch
                className="self-end"
                checked={draft.status === 'approved'}
                onCheckedChange={checked => {
                  // handle status change logic
                }}
                defaultChecked
              >
                Approved?
              </Switch>
            </CardBody>
          </Card>

          {/* Draft Content Preview */}
          <Card>
            <CardHeader>Draft Content</CardHeader>
            <CardBody>
              <pre className="text-sm whitespace-pre-wrap bg-gray-50 p-3 rounded-md overflow-x-auto">{draft.content}</pre>
            </CardBody>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-2 justify-end pt-2">
            <Button onClick={handleRequestRevision}>Request Revision</Button>
            <Button onClick={handleReject}>Reject</Button>
            <Button variant="primary" onClick={handleApprove}>Approve</Button>
            <Button variant="danger" onClick={handleForceApprove}>
              Force Approve
            </Button>
          </div>
        </DialogBody>
      </Dialog>
    </Dialog>
  );
}