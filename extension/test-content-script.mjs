import { readFileSync } from "node:fs";
import vm from "node:vm";


const source = readFileSync(new URL("./content-script.js", import.meta.url), "utf8");

const fixtures = [
  {
    name: "linkedin",
    host: "www.linkedin.com",
    title: "Python AI Full Stack Engineer | DemoFin Analytics",
    selectors: {
      ".job-details-jobs-unified-top-card__job-title": "Python AI Full Stack Engineer",
      ".job-details-jobs-unified-top-card__company-name": "DemoFin Analytics",
      ".job-details-jobs-unified-top-card__primary-description-container": "DemoFin Analytics · Bengaluru, Karnataka, India · Remote",
      ".jobs-description-content__text": "We need Python, Django, React, SQL, ETL pipelines, cloud fundamentals, and AI agent workflow automation.",
    },
    expected: {
      source: "linkedin",
      title: "Python AI Full Stack Engineer",
      company: "DemoFin Analytics",
      locationIncludes: "Bengaluru",
      descriptionIncludes: "AI agent workflow automation",
    },
  },
  {
    name: "naukri",
    host: "www.naukri.com",
    title: "Senior .NET Full Stack Developer",
    selectors: {
      ".styles_jd-header-title__rZwM1": "Senior .NET Full Stack Developer",
      ".styles_jd-header-comp-name__MvqAI": "RetailCloud Systems",
      ".styles_jhc__location__W_pVs": "Pune",
      ".styles_JDC__dang-inner-html__h0K4t": "Required skills include ASP.NET Core, C#, Angular, SQL Server, Entity Framework, REST APIs, and Azure.",
    },
    expected: {
      source: "naukri",
      title: "Senior .NET Full Stack Developer",
      company: "RetailCloud Systems",
      locationIncludes: "Pune",
      descriptionIncludes: "ASP.NET Core",
    },
  },
  {
    name: "indeed",
    host: "in.indeed.com",
    title: "Data Engineer",
    selectors: {
      "[data-testid='jobsearch-JobInfoHeader-title']": "Data Engineer",
      "[data-company-name='true']": "InsightOps",
      "[data-testid='job-location']": "Hyderabad, Telangana",
      "#jobDescriptionText": "Build Python ETL pipelines, SQL transformations, dashboards, and cloud data workflows.",
    },
    expected: {
      source: "indeed",
      title: "Data Engineer",
      company: "InsightOps",
      locationIncludes: "Hyderabad",
      descriptionIncludes: "cloud data workflows",
    },
  },
  {
    name: "generic company careers page",
    host: "careers.example.com",
    title: "Java Backend Engineer",
    selectors: {
      "h1": "Java Backend Engineer",
      "[class*='company' i]": "ProductWorks",
      "[class*='location' i]": "Remote",
      "[class*='description' i]": "Work on Java, Spring Boot, PostgreSQL, Kafka, Redis, Docker, and Kubernetes services.",
    },
    expected: {
      source: "generic",
      title: "Java Backend Engineer",
      company: "ProductWorks",
      locationIncludes: "Remote",
      descriptionIncludes: "Kubernetes",
    },
  },
];

for (const fixture of fixtures) {
  const result = runFixture(fixture);
  assertEqual(`${fixture.name} source`, result.source, fixture.expected.source);
  assertEqual(`${fixture.name} title`, result.extractedTitle, fixture.expected.title);
  assertEqual(`${fixture.name} company`, result.extractedCompany, fixture.expected.company);
  assertIncludes(`${fixture.name} location`, result.extractedLocation, fixture.expected.locationIncludes);
  assertIncludes(`${fixture.name} description`, result.extractedDescription, fixture.expected.descriptionIncludes);
  console.log(`[PASS] ${fixture.name}`);
}

console.log(`\nExtension content parser fixtures passed (${fixtures.length} sites).`);


function runFixture(fixture) {
  const context = {
    chrome: {
      runtime: {
        onMessage: {
          addListener: () => undefined,
        },
      },
    },
    window: {
      location: {
        hostname: fixture.host,
        href: `https://${fixture.host}/jobs/demo`,
      },
      getSelection: () => ({ toString: () => "" }),
    },
    document: {
      title: fixture.title,
      body: { innerText: Object.values(fixture.selectors).join("\n") },
      querySelector: (selector) => {
        const text = fixture.selectors[selector];
        return text ? { innerText: text } : null;
      },
    },
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(source, context, { filename: "content-script.js" });
  return vm.runInContext("extractJobDetails()", context);
}

function assertEqual(label, actual, expected) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, received ${JSON.stringify(actual)}`);
  }
}

function assertIncludes(label, actual, expectedPart) {
  if (!actual || !actual.includes(expectedPart)) {
    throw new Error(`${label}: expected ${JSON.stringify(actual)} to include ${JSON.stringify(expectedPart)}`);
  }
}
