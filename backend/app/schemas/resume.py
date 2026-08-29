"""Resume and Candidate Profile schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    """Education entry."""

    institution: str = Field(..., description="School, college, or university name")
    degree: Optional[str] = Field(None, description="Degree or qualification (e.g., B.S., MBA)")
    field_of_study: Optional[str] = Field(None, description="Field of study or major")
    start_date: Optional[str] = Field(None, description="Start date or year")
    end_date: Optional[str] = Field(None, description="End date or year")
    gpa: Optional[str] = Field(None, description="GPA if mentioned")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Skill(BaseModel):
    """Individual skill."""

    name: str = Field(..., description="Name of the skill")
    proficiency: Optional[str] = Field(
        None, description="Proficiency level (e.g., Expert, Intermediate, Beginner)"
    )
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Technology(BaseModel):
    """Technology, tool, or framework."""

    name: str = Field(..., description="Name of technology/tool/framework")
    category: Optional[str] = Field(
        None, description="Category (e.g., Language, Framework, Database, Cloud)"
    )
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Experience(BaseModel):
    """Work experience entry."""

    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job title or position")
    start_date: Optional[str] = Field(None, description="Start date or year")
    end_date: Optional[str] = Field(None, description="End date or year (or 'Present')")
    duration_months: Optional[int] = Field(None, description="Duration in months")
    description: Optional[str] = Field(None, description="Job responsibilities and achievements")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Project(BaseModel):
    """Project entry."""

    name: str = Field(..., description="Project name or title")
    description: Optional[str] = Field(None, description="Project description")
    technologies: Optional[list[str]] = Field(None, description="Technologies used")
    role: Optional[str] = Field(None, description="Candidate's role in the project")
    date: Optional[str] = Field(None, description="Project date or timeframe")
    url: Optional[str] = Field(None, description="Project URL or GitHub link if mentioned")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Certification(BaseModel):
    """Certification or credential."""

    name: str = Field(..., description="Certification name")
    issuer: Optional[str] = Field(None, description="Issuing organization")
    date: Optional[str] = Field(None, description="Date obtained")
    url: Optional[str] = Field(None, description="Verification URL if mentioned")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Achievement(BaseModel):
    """Notable achievement or award."""

    title: str = Field(..., description="Achievement or award title")
    description: Optional[str] = Field(None, description="Description of achievement")
    date: Optional[str] = Field(None, description="Date of achievement")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class Claim(BaseModel):
    """Specific claim made in the resume that can be verified during interview."""

    claim_id: Optional[str] = Field(
        None, description="Stable identifier assigned when the claim is persisted"
    )
    claim_text: str = Field(..., description="The specific claim made in the resume")
    category: str = Field(
        ...,
        description="Category: quantitative (e.g., '18% improvement'), technical (e.g., 'BERT-based system'), domain (e.g., 'ML expert')",
    )
    context: Optional[str] = Field(
        None, description="Context from resume (what project/role this relates to)"
    )
    resume_evidence: str = Field(
        ..., description="Exact quote from resume where claim appears"
    )


class CandidateIdentity(BaseModel):
    """Candidate personal and professional identity."""

    full_name: Optional[str] = Field(None, description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, state, or country")
    resume_evidence: Optional[str] = Field(
        None, description="Direct quote or text from resume"
    )


class CandidateProfile(BaseModel):
    """Complete candidate profile extracted from resume."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identity": {
                    "full_name": "Jane Doe",
                    "email": "jane@example.com",
                    "location": "San Francisco, CA",
                },
                "professional_summary": "Machine Learning Engineer with 5 years of experience",
                "education": [
                    {
                        "institution": "Stanford University",
                        "degree": "M.S.",
                        "field_of_study": "Computer Science",
                        "end_date": "2020",
                    }
                ],
                "skills": [
                    {"name": "Machine Learning", "proficiency": "Expert"},
                    {"name": "Python", "proficiency": "Expert"},
                ],
                "technologies": [
                    {"name": "TensorFlow", "category": "Framework"},
                    {"name": "PyTorch", "category": "Framework"},
                ],
                "experience": [
                    {
                        "company": "Tech Corp",
                        "position": "ML Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                    }
                ],
                "projects": [
                    {
                        "name": "BERT Sentiment Analysis",
                        "technologies": ["BERT", "PyTorch"],
                        "description": "Built a sentiment analysis system",
                    }
                ],
                "claims": [
                    {
                        "claim_text": "Improved model accuracy by 18%",
                        "category": "quantitative",
                        "context": "Sentiment analysis project",
                        "resume_evidence": "Improved model accuracy by 18%",
                    }
                ],
            }
        }
    )

    identity: CandidateIdentity = Field(..., description="Candidate identity information")
    professional_summary: Optional[str] = Field(
        None, description="Professional summary or objective from resume"
    )
    education: list[Education] = Field(
        default_factory=list, description="Education entries"
    )
    skills: list[Skill] = Field(default_factory=list, description="Skills extracted")
    technologies: list[Technology] = Field(
        default_factory=list, description="Technologies and tools"
    )
    experience: list[Experience] = Field(
        default_factory=list, description="Work experience entries"
    )
    projects: list[Project] = Field(default_factory=list, description="Projects")
    certifications: list[Certification] = Field(
        default_factory=list, description="Certifications"
    )
    achievements: list[Achievement] = Field(
        default_factory=list, description="Achievements and awards"
    )
    claims: list[Claim] = Field(
        default_factory=list, description="Claims that can be investigated during interview"
    )
    languages: list[str] = Field(
        default_factory=list, description="Programming or spoken languages"
    )