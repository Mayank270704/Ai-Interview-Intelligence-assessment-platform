import Link from "next/link";

export default function HomePage() {
  return (
    <main className="narrow">
      <h1>AI Interview Intelligence</h1>
      <p>Your workspace for focused interview practice and evidence-based assessment.</p>
      <Link href="/resume/upload" className="button">
        Upload your resume to begin
      </Link>
    </main>
  );
}
