/**
 * A hosted answer at a chosen level of detail, and the same answer later with more.
 *
 * The answer is model-written, so it is fetched again rather than asked again: `more` reads the
 * stored answer at a higher level, word for word, and bills nothing. The body's type follows the
 * level: a section at or below it is present (null when its step did not run), and one above it is absent.
 */
import type { components } from "./schema.ts";

export type AnswerDetail = components["schemas"]["AnswerDetail"];
type View = components["schemas"]["AnswerView"];

type FindingsSections =
  | "findings"
  | "lead"
  | "sections"
  | "results"
  | "appended_finding_ids"
  | "background_finding_ids"
  | "interpretation"
  | "subject"
  | "selection"
  | "multi_valued_slots"
  | "boundary"
  | "change"
  | "obligations";
type ClaimsSections = "claims";
type EverythingSections = "read_documents" | "sources" | "stage_events";
type Sections = FindingsSections | ClaimsSections | EverythingSections;

type Above<D extends AnswerDetail> = D extends "answer"
  ? Sections
  : D extends "findings"
    ? ClaimsSections | EverythingSections
    : D extends "claims"
      ? EverythingSections
      : never;

/** The answer's body at level `D`. */
export type AnswerAt<D extends AnswerDetail> = Omit<View, Sections> & {
  [K in Exclude<Sections, Above<D>>]-?: Exclude<View[K], undefined>;
};

export class Answer<D extends AnswerDetail = "answer"> {
  readonly body: AnswerAt<D>;
  private readonly fetchStored: (path: string) => Promise<unknown>;

  constructor(body: AnswerAt<D>, fetchStored: (path: string) => Promise<unknown>) {
    this.body = body;
    this.fetchStored = fetchStored;
  }

  /** This same answer at `detail`, read from where the response says it is served. */
  async more<L extends AnswerDetail>(detail: L): Promise<Answer<L>> {
    const links = this.body.more;
    if (links === null || links === undefined) {
      const reason = this.body.more_unavailable_reason ?? "unknown";
      throw new Error(`this answer has no more detail to fetch: ${reason}`);
    }
    const link = (links as Record<string, string | undefined>)[detail];
    if (link === undefined) {
      throw new Error(`"${detail}" is not above this answer's level "${this.body.detail}"`);
    }
    return new Answer<L>((await this.fetchStored(link)) as AnswerAt<L>, this.fetchStored);
  }
}
