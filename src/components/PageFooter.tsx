export function PageFooter() {
  return (
    <footer className="border-t border-border bg-surface py-8">
      <div className="mx-auto flex max-w-[1500px] flex-col justify-between gap-4 px-4 text-sm text-muted-foreground sm:flex-row lg:px-8">
        <p>L. D. College of Engineering, Opp. Gujarat University, Navrangpura, Ahmedabad</p>
        <div className="flex gap-5">
          <a href="https://ldce.ac.in" target="_blank" rel="noreferrer">
            Admission
          </a>
          <a href="https://ldce.ac.in" target="_blank" rel="noreferrer">
            Contact
          </a>
          <a href="https://ldce.ac.in" target="_blank" rel="noreferrer">
            Circulars
          </a>
        </div>
      </div>
    </footer>
  );
}
