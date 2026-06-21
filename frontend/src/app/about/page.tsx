"use client";

import { AppShell, Card } from "@/components/AppShell";
import { IndustryToggle } from "@/components/IndustryToggle";

export default function AboutPage() {
  return (
    <AppShell>
      <h1 className="mb-8 text-center text-3xl font-extrabold text-navy">
        Explanations of Buttons
      </h1>
      <div className="grid gap-6 md:grid-cols-3">
        <Card title="Industry Toggle">
          <div className="mb-4">
            <IndustryToggle />
          </div>
          <p className="text-sm text-muted">
            Lets you choose the industry you are in. Line of Sight is personalized to
            the industry in terms of calculations, required data, and the look and feel
            of the software (Corporate = amber, Hospital = teal).
          </p>
        </Card>
        <Card title="Feedback Button">
          <p className="text-sm text-muted">
            A feedback form that measures product success across touch points. It takes
            you to a quick form that helps drive product-modification decisions.
          </p>
        </Card>
        <Card title="Tool Bar">
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
            <li>Features — inspect our offerings</li>
            <li>About us — learn more about Line of Sight</li>
            <li>Sign out — leave the software at any point</li>
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}
