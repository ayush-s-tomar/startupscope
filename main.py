from crew.crew import run_crew

if __name__ == "__main__":
    company = input("Enter company name to research: ").strip()
    print(f"\nStarting research on: {company}\n{'='*50}\n")

    result, saved_path = run_crew(company)

    print(f"\n{'='*50}")
    print(f"Report saved to: {saved_path}")
    print(f"\n{result}")
