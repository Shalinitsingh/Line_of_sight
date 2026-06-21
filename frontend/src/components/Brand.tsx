export function Brand() {
  return (
    <div className="space-y-6">
      <p className="text-3xl font-extrabold text-brandblue line-through decoration-2">
        Report
      </p>
      <h2 className="text-4xl font-extrabold text-accent">
        Create Insights{" "}
        <span className="text-xl font-bold text-navy">in 5 Easy Steps</span>
      </h2>
      <div className="space-y-6 pt-4 text-lg font-semibold text-navy">
        <div className="flex gap-16">
          <span>Ingest</span>
          <span>Ask</span>
          <span>Modify</span>
        </div>
        <div className="flex gap-16 pl-6">
          <span>Select</span>
          <span>Generate</span>
        </div>
      </div>
    </div>
  );
}
