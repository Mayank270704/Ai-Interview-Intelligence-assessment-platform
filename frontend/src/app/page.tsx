import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <span className="eyebrow">AI Interview Intelligence</span>
        <h1>Interview practice that adapts to your resume</h1>
        <p className="lede">
          Upload your resume and get a live, evidence-based interview: questions grounded in your
          actual experience, follow-ups that probe your resume claims, and a clear summary of what
          you demonstrated.
        </p>
        <div className="actions">
          <Link href="/resume/upload" className="button">
            Upload your resume to begin
          </Link>
        </div>
      </section>

      <div className="feature-grid">
        <div className="feature">
          <div className="feature-icon">1</div>
          <h3>Resume-grounded questions</h3>
          <p>Every question is generated from your real skills, projects, and claims.</p>
        </div>
        <div className="feature">
          <div className="feature-icon">2</div>
          <h3>Adaptive follow-ups</h3>
          <p>Difficulty and depth adjust turn by turn based on how you answer.</p>
        </div>
        <div className="feature">
          <div className="feature-icon">3</div>
          <h3>Evidence-based results</h3>
          <p>See exactly which concepts and resume claims were verified by your answers.</p>
        </div>
      </div>
    </main>
  );
}
