# Split Columnar Keyboard Project Roadmap

A roadmap for developing a custom split columnar mechanical keyboard with a strong focus on acoustic character, reproducible engineering, declarative configuration, and LLM/MCP-assisted iteration.

> **Guiding principle:** the specification is the source of truth; CAD/EDA projects are engineering implementations; generated manufacturing files are release artefacts; prototypes and controlled tests determine whether a design actually works.

## 1. Project goals

### Primary goal

Develop a usable, manufacturable split columnar keyboard whose acoustic character is a major design objective, and whose design can be iterated through controlled, documented experiments.

### Supporting goals

- Maintain a parametric, configuration-driven layout and mechanical design.
- Keep electronic, mechanical, firmware, and presentation assets consistent.
- Automate repeatable checks and exports instead of manually maintaining duplicate data.
- Use LLM agents to research, propose changes, generate candidates, and interpret test results without allowing them to silently bypass constraints.
- Eventually produce high-quality product renders, engineering visualisations, and promotional video based on the real design.

### Requirements to decide early

- [ ] Key-count target and minimum acceptable number of keys.
- [ ] Mandatory versus optional rotary encoder.
- [ ] Wired, wireless, or hybrid connection architecture.
- [ ] Controller and firmware family (evaluate QMK and ZMK against the intended architecture).
- [ ] Split interconnect and power strategy.
- [ ] Switch family, hot-swap requirements, and stabiliser requirements.
- [ ] Manufacturing methods available for the PCB, plate, and enclosure.
- [ ] Budget for initial prototypes and later revisions.
- [ ] Acoustic preferences expressed as both a listening description and measurable comparisons.

Do not treat provisional decisions as established engineering facts. Record the status of each decision as `fixed`, `provisional`, `candidate`, `measured`, or `undecided`.

---

## 2. Recommended toolchain

| Responsibility | Initial choice | Notes |
|---|---|---|
| Declarative design specification | YAML + JSON Schema (or equivalent validation) | Store intent, constraints, parameters, statuses, and acceptance criteria. |
| Layout generation | Ergogen | Useful for ergonomic key coordinates, outlines, plates, cases, and an initial unrouted PCB layout. |
| PCB and schematic | KiCad | Authoritative electrical schematic and routed PCB. |
| Mechanical CAD generation | CadQuery | Generate parametric plate and enclosure geometry from shared coordinates and declared parameters. |
| Interactive mechanical inspection | FreeCAD | Inspect STEP models, examine clearances, and make deliberate human-directed edits where needed. Keep source scripts/specification authoritative. |
| Product visualisation | Blender | Materials, lighting, studio scenes, close-ups, exploded views, animation, and final image/video rendering. |
| Automation | Python + command-line tools + MCP servers | Validate configuration, call generators, export files, run checks, and record results. |
| Version control | Git | Preserve baselines, experiments, decisions, and generator versions. Use branches/worktrees for candidate designs. |
| Firmware | QMK or ZMK | Select based on the controller, split architecture, and connectivity requirements. |

**Toolchain rule:** do not force every job into one application. Use explicit interfaces between tools and maintain one authoritative source for each design fact.

**Important versioning note:** pin software versions used for a release, especially KiCad and any MCP server or script interacting with its APIs. Verify that each MCP server supports the installed versions before relying on it.

---

## 3. Suggested repository structure

```text
split-keyboard/
├── README.md
├── ROADMAP.md
├── pyproject.toml
├── spec/
│   ├── keyboard.yaml
│   ├── layout.yaml
│   ├── acoustics.yaml
│   ├── electronics.yaml
│   ├── manufacturing.yaml
│   └── schema/
│       └── keyboard.schema.json
├── layout/
│   └── ergogen/                 # Ergogen config and source files
├── electronics/
│   └── kicad/                   # KiCad schematic and PCB project
├── generators/
│   ├── validate_spec.py
│   ├── export_layout.py
│   ├── generate_plate.py
│   ├── generate_case.py
│   ├── build_release.py
│   └── common/                  # Shared coordinates, units, helpers
├── firmware/
├── experiments/
│   ├── proposed/
│   ├── completed/
│   └── results/
├── decisions/
│   └── README.md
├── tests/
│   ├── test_spec.py
│   ├── test_layout.py
│   ├── test_geometry.py
│   ├── test_clearances.py
│   └── test_release.py
├── visualisation/
│   ├── blender/                 # Rendering scenes and scripts
│   ├── materials/
│   └── storyboards/
├── generated/                   # Derived outputs; never the authoritative source
│   ├── layout/
│   ├── mechanical/
│   ├── pcb/
│   ├── firmware/
│   ├── reports/
│   └── release/
└── docs/
    ├── assembly.md
    ├── testing.md
    └── manufacturing.md
```

Adjust the directory structure if necessary, but keep specification/source files separate from generated outputs.

---

## 4. End-to-end development phases

## Phase 0 — Set up the project and design rules

**Purpose:** create the foundation before design work becomes complicated.

### Tasks

- [ ] Create the Git repository and directory structure.
- [ ] Add this roadmap and a short project README.
- [ ] Choose a units convention (millimetres and degrees for mechanical geometry).
- [ ] Create the initial specification files and schema.
- [ ] Define parameter statuses: `fixed`, `provisional`, `candidate`, `measured`, `undecided`.
- [ ] Decide how design revisions, generator versions, experiment IDs, and release artefacts will be identified.
- [ ] Establish a rule that generated files are reproducible from committed inputs or accompanied by metadata identifying their inputs.

### Exit criteria

- The repository has a clear source-of-truth policy.
- The specification can be checked by a validator.
- A proposed change can be represented as a structured parameter patch rather than an informal prompt alone.

## Phase 1 — Define the product and acoustic intent

**Purpose:** specify what the design is optimising before exploring the solution.

### Tasks

- [ ] Define the keyboard architecture, key-count requirements, encoder requirement, split strategy, and connectivity.
- [ ] Separate mandatory constraints from preferences.
- [ ] Define ergonomic objectives: column stagger, splay, thumb reach, key spacing, and intended hand posture.
- [ ] Describe the target sound perceptually (for example: full, smooth, clear attack, controlled decay) and list unwanted characteristics (for example: metallic ping, rattling, excessive or inconsistent resonance).
- [ ] Identify the main acoustic variables: switch, spring, keycaps, plate material/thickness/geometry, mounting, case stiffness, internal volume, damping, stabilisers, and desk contact.
- [ ] Record which variables are initially fixed during testing.
- [ ] List cost, fabrication, assembly, portability, and repairability constraints.
- [ ] Mark unknowns as undecided instead of silently inventing values.

### Deliverables

- `spec/keyboard.yaml`
- `spec/layout.yaml`
- `spec/acoustics.yaml`
- `spec/electronics.yaml`
- `spec/manufacturing.yaml`

### Exit criteria

- Every critical requirement has a status and a validation method.
- The acoustic target is written clearly enough to guide experiments without pretending that subjective sound quality is already quantifiable.

## Phase 2 — Design and validate the layout

**Purpose:** settle the ergonomics and key positions before locking down the rest of the design.

### Tasks

- [ ] Explore key count, finger-column staggering, column splay, thumb cluster, encoder position, and split angle.
- [ ] Use Ergogen to generate the initial key coordinates and layout-related geometry.
- [ ] Inspect visualisations and generated outputs.
- [ ] Check key spacing, switch/plate assumptions, hand reach, thumb accessibility, and obvious collisions.
- [ ] Create a small set of deliberate layout variants rather than repeatedly changing many parameters at once.
- [ ] Export a canonical coordinate file for downstream generators.
- [ ] Freeze a layout baseline in Git once it is acceptable for electronic and mechanical development.

### Deliverables

- Ergogen configuration.
- Canonical key-position export with units and orientation documented.
- Layout review and a tagged baseline revision.

### Exit criteria

- The layout meets key-count and ergonomic constraints.
- Key positions can be regenerated reproducibly.
- PCB and mechanical generators can consume the same coordinate source.

## Phase 3 — Create the first integrated geometry prototype

**Purpose:** prove the layout can become physical parts before investing in a complex PCB design.

### Tasks

- [ ] Generate a basic plate from the layout coordinates.
- [ ] Generate a simple enclosure or tray with provisional dimensions.
- [ ] Use inexpensive prints or placeholder parts to check key spacing, overall size, split placement, thumb cluster, and desk interaction.
- [ ] Confirm switch and stabiliser cut-out dimensions against authoritative component documentation.
- [ ] Record any ergonomic or packaging changes and update the layout source rather than hand-editing derived geometry.

### Deliverables

- Basic plate DXF/STEP/STL as appropriate.
- Basic case STEP/STL.
- Visual or physical fit-check notes.

### Exit criteria

- The major layout and packaging assumptions are plausible.
- Known fit issues are corrected before PCB routing becomes expensive to change.

## Phase 4 — Design the schematic and PCB in KiCad

**Purpose:** produce a real electrical design, not merely an unrouted collection of switch footprints.

### Tasks

- [ ] Choose the controller and confirm its operating voltage, available pins, USB approach, and firmware support.
- [ ] Define the switch matrix and diode arrangement.
- [ ] Design the split interconnect and power architecture.
- [ ] Add the encoder, connectors, and optional peripherals if required.
- [ ] Choose verified component symbols and footprints; verify pin numbering and physical dimensions against datasheets.
- [ ] Create the KiCad schematic and run ERC.
- [ ] Import or reproduce the canonical layout coordinates in the PCB.
- [ ] Position components and route the PCB, respecting mechanical keep-outs and fabrication rules.
- [ ] Run DRC and inspect all violations; do not blindly waive warnings.
- [ ] Check matrix connectivity, diode direction, controller pin mapping, connectors, power, board outline, mounting holes, and switch footprint locations.
- [ ] Export a PCB STEP model for mechanical integration.

### Deliverables

- KiCad project, schematic, and PCB.
- ERC/DRC reports.
- Board STEP model and component-placement export for CAD integration.

### Exit criteria

- The schematic and PCB agree.
- The PCB is electrically and geometrically checked.
- Component footprints have been verified against real parts or reliable documentation.

**Important:** passing ERC/DRC does not prove that a board is functionally correct. It is necessary evidence, not complete sign-off.

## Phase 5 — Develop the plate and enclosure as a coordinated assembly

**Purpose:** create manufacturable mechanical parts based on the actual PCB and switch geometry.

### Tasks

- [ ] Use CadQuery to generate the switch plate, case, mounts, cavities, gaskets, screw holes, cable openings, and relevant internal features.
- [ ] Drive key cut-outs and switch positions from the canonical layout coordinates.
- [ ] Use the real PCB outline, thickness, holes, connectors, and component geometry as references.
- [ ] Define and test tolerances; avoid treating nominal dimensions as perfect physical dimensions.
- [ ] Check tool access, fastener installation, assembly sequence, and ease of service.
- [ ] Export STEP for mechanical exchange, DXF for suitable 2D fabrication, and STL/3MF for 3D printing.
- [ ] Inspect models in FreeCAD and make deliberate human-directed adjustments where needed.
- [ ] If a CAD edit changes an authoritative dimension, propagate it back into the specification or source generator. Avoid untracked changes to derived files.
- [ ] Combine PCB, plate, enclosure, and available component models into a full assembly.
- [ ] Run automated clearance and alignment checks.

### Deliverables

- Parametric CadQuery source.
- Plate and case STEP/DXF/STL/3MF files as appropriate.
- Combined assembly model.
- Geometry and clearance report.

### Exit criteria

- The assembly fits digitally with documented tolerances.
- All essential openings, mounting features, and component clearances have been checked.

## Phase 6 — Implement and verify firmware

**Purpose:** make the electrical design usable.

### Tasks

- [ ] Choose QMK or ZMK based on controller and architecture.
- [ ] Configure matrix rows/columns and diode direction consistently with the schematic.
- [ ] Implement the keymap, layers, encoder behaviour, split communication, and optional features.
- [ ] Build firmware in a reproducible environment.
- [ ] Add checks that compare declared matrix and controller mappings with the firmware configuration where practical.
- [ ] Document flashing and recovery procedures.

### Deliverables

- Firmware source/configuration.
- Repeatable build instructions.
- Pin mapping and keymap documentation.

### Exit criteria

- Firmware builds successfully and its mapping agrees with the electronics design.

## Phase 7 — Automate manufacturing outputs

**Purpose:** create a repeatable release pipeline from the authoritative design files.

### PCB fabrication outputs

- [ ] Run KiCad CLI ERC/DRC and preserve the reports.
- [ ] Export Gerber layers from the final `.kicad_pcb`.
- [ ] Export drill files.
- [ ] Export PCB STEP if required for assembly integration.
- [ ] Inspect the Gerbers in a viewer and confirm the board outline, layer stack, holes, and dimensions.

### Assembly outputs

- [ ] Populate correct component metadata in the KiCad project.
- [ ] Generate the BOM from schematic component fields, supplemented only when the assembly house requires additional information.
- [ ] Generate the CPL/centroid/pick-and-place file from PCB footprint placements.
- [ ] Format and validate both against the selected assembler's current requirements.
- [ ] Confirm reference designators agree between BOM and CPL.
- [ ] Explicitly handle components not intended for automated assembly.

### Mechanical outputs

- [ ] Export final plate and case files from the controlled CAD generators.
- [ ] Include a complete keyboard BOM as well as any PCB assembler-specific BOM.
- [ ] Generate assembly drawings and notes where they reduce ambiguity.

### Release validation

- [ ] Verify expected files exist and are non-empty.
- [ ] Record specification revision, Git commit, tool versions, and generator versions in a release manifest.
- [ ] Create a versioned archive of the full manufacturing package.
- [ ] Require human approval before sending files to a fabricator or ordering parts.

### Example release structure

```text
generated/release/v0.1.0/
├── pcb/
│   ├── gerbers/
│   ├── drill/
│   ├── bom.csv
│   ├── positions.csv
│   └── pcb.step
├── mechanical/
│   ├── plate.dxf
│   ├── plate.step
│   ├── case.step
│   ├── case.stl
│   └── assembly.step
├── firmware/
├── reports/
│   ├── erc.txt
│   ├── drc.txt
│   ├── geometry-checks.json
│   └── release-checks.json
└── release-manifest.json
```

**Exit criteria:** the package can be regenerated from committed source, has passed the defined release checks, and is ready for human review.

## Phase 8 — Build physical prototypes and test acoustics

**Purpose:** test the real object, not just the model.

### Tasks

- [ ] Manufacture the PCB and required mechanical parts.
- [ ] Inspect boards and parts before assembly.
- [ ] Test continuity, power, controller operation, matrix scanning, encoder input, and split communication.
- [ ] Verify physical fit, screw access, connector access, stability, and assembly sequence.
- [ ] Record acoustic samples using a consistent recording setup.
- [ ] Keep microphone position/orientation, gain, environment, switches, keycaps, lubrication, and keypress protocol fixed when comparing candidates.
- [ ] Analyse frequency spectra, decay envelopes, tonal peaks, and (where useful) sound pressure level.
- [ ] Conduct listening comparisons; metrics support but do not replace listening judgement.
- [ ] Record issues and create focused experiments to address them.

### Deliverables

- Working prototype.
- Baseline and comparison recordings.
- Test report, photos, and revision-specific findings.

### Exit criteria

- The prototype works electrically and mechanically.
- Acoustic judgements are grounded in real recordings.
- The current baseline has reproducible build instructions.

## Phase 9 — Establish the LLM/MCP experimentation workflow

This workflow supports all phases, but it becomes substantially more useful once the generators and baseline are working.

### Suggested MCP operations

Implement or select tools that provide narrow, auditable operations such as:

- `spec.get`: read the current specification.
- `spec.validate`: validate schema, units, bounds, and cross-file constraints.
- `experiment.propose`: create a hypothesis and candidate parameter patch.
- `candidate.create`: create a Git branch or worktree for the experiment.
- `candidate.generate`: run selected layout/CAD/EDA generation steps.
- `candidate.check`: run geometry, clearance, ERC, DRC, and other available checks.
- `acoustics.compare`: compare specified recordings and metrics to a baseline.
- `experiment.record`: store results and interpretation.
- `candidate.promote`: promote a candidate only after required approval.

These names describe the intended interface; they are not claims that a particular server provides all these tools out of the box.

### Experiment rules

- [ ] Every experiment has a unique ID, a baseline revision, a hypothesis, and a reasoned mechanism.
- [ ] Each candidate changes only the intended variables, unless the experiment is explicitly designed to test interactions.
- [ ] The experiment defines controls, checks, measurements, and a decision rule before the test.
- [ ] Preserve failed candidates and results.
- [ ] Do not let agents weaken or edit acceptance criteria merely to make a candidate pass.
- [ ] Separate the agent's interpretation from measured data.
- [ ] Store configuration snapshots, Git commits, tool versions, and generated artefact hashes with results.
- [ ] Keep fabrication orders, purchases, and promotion of major design decisions behind human approval.

### First acoustic experiment candidates

1. Switch and keycap baseline comparison.
2. Plate material/thickness comparison.
3. Mounting stiffness and mount-position comparison.
4. Case internal volume and wall-stiffness comparison.
5. Damping configuration comparison.
6. Controlled interaction experiments once individual effects are understood.

Avoid changing switch, plate, mount, case, and damping all at once during early testing. If the result changes, you otherwise will not know why.

## Phase 10 — Create realistic product renders

**Purpose:** make attractive visuals based on the actual engineering geometry.

### Pipeline

- [ ] Export CAD geometry from CadQuery/FreeCAD and a board model from KiCad.
- [ ] Convert models to suitable mesh formats when importing into Blender.
- [ ] Preserve separate objects for keycaps, switches, plate, PCB, case, fasteners, knobs, and other visible elements.
- [ ] Use the engineering model as the source for proportions and interfaces.
- [ ] Create a separate presentation scene for cosmetic details, materials, lighting, and staging. Presentation-only changes must not alter manufacturing files.
- [ ] Build reusable physically based materials: polymer, textured plastic, anodised metal, translucent parts, PCB solder mask, etc.
- [ ] Create reusable lighting/camera setups for dark studio, bright minimalist, macro, and exploded-view renders.
- [ ] Create automated render scripts where useful, but keep artistic review in the loop.
- [ ] Generate detail renders of the encoder, plate/mounting design, case surfaces, and internal construction.

### Deliverables

- Blender project and reusable materials.
- High-resolution still renders.
- Exploded technical visualisations.
- Clearly identified concept imagery for features not yet implemented or validated.

**Important:** visually convincing is not the same as physically accurate. Avoid presenting optional or unbuilt features as confirmed product features.

## Phase 11 — Produce promotional video

**Purpose:** communicate the product's design and differentiators clearly.

### Suggested video components

- [ ] Hero reveal with deliberate camera movement and studio lighting.
- [ ] Slow product orbit and detail shots.
- [ ] Exploded assembly and reassembly animation.
- [ ] Feature sequences for columnar geometry, encoder, materials, mounting system, and repairability.
- [ ] Accurate on-screen labels and technical diagrams where they add clarity.
- [ ] Actual recorded keyboard audio, captured from the real prototype under documented conditions.
- [ ] Editing, colour grade, titles, captions, sound mix, and export to several aspect ratios.
- [ ] Produce one master video and derive shorter clips for project updates and social platforms.

Blender can generate animation frames and scripted camera/object motion. Editing can be completed in a video editor. AI tools can help with storyboards, scripting, shot lists, and repetitive scene setup, but the final video should accurately represent the real design and sound.

### Deliverables

- Storyboard and shot list.
- Master promotional video.
- Short-format clips.
- Product stills and exploded views.

## Phase 12 — Final verification and manufacturing release

**Purpose:** freeze a candidate and verify the exact design that will be made.

### Tasks

- [ ] Resolve prototype issues and update the specification.
- [ ] Run the full electrical, mechanical, firmware, and manufacturing validation suite.
- [ ] Regenerate all manufacturing files from the final release commit.
- [ ] Build at least one verification prototype from that exact release where feasible.
- [ ] Confirm component availability, alternates, lead times, BOM cost, and assembly instructions.
- [ ] Validate final packaging and shipping constraints if relevant.
- [ ] Publish known limitations and remaining risks rather than hiding them.

### Deliverables

- Versioned production-candidate release.
- Full source and manufacturing archive.
- Final BOM and cost model.
- Assembly and flashing instructions.
- Verification report and final prototype evidence.

## Phase 13 — Prepare a public launch (optional)

If the project eventually becomes a Kickstarter campaign or other product launch:

- [ ] Distinguish demonstrated features from planned features.
- [ ] Prepare accurate product photography, renders, and video.
- [ ] Calculate realistic prototype, tooling, manufacturing, packaging, shipping, tax, and contingency costs.
- [ ] Confirm supplier and manufacturing assumptions.
- [ ] Document the development process, test results, manufacturing plan, schedule risks, and quality-control approach.
- [ ] Avoid making claims about sound, durability, delivery dates, or final materials that are not supported by evidence.

---

## 5. Source-of-truth and change-control rules

1. **One authoritative source per fact.** Key locations, for example, should come from one canonical layout source and be consumed by every downstream generator.
2. **Generated files are not authoritative.** If a manual edit changes an important dimension, update the specification or generator and regenerate outputs.
3. **Keep a feasibility gate before optimisation.** A candidate must meet minimum electrical, geometric, ergonomic, and manufacturing requirements before it competes on subjective preferences.
4. **Never equate a successful export with a correct design.** Inspect outputs and validate the underlying engineering.
5. **Use Git for every meaningful experiment.** Preserve candidate branches, configuration snapshots, decision records, tool versions, and results.
6. **Do not let an agent change the rules to make itself pass.** Validation thresholds and acceptance criteria require explicit review when changed.
7. **Protect the manufacturing baseline.** Agents should work in branches/worktrees and should not silently overwrite the accepted design.
8. **Human approval before irreversible actions.** This includes manufacturing release, purchases, major architecture changes, and public claims about product capability.

## 6. Definition of a good iteration

Every significant design experiment should record:

- Experiment ID and date.
- Baseline revision and configuration hash.
- Hypothesis and expected causal mechanism.
- Parameter paths to change and candidate values.
- Variables held constant.
- Geometry/electrical/manufacturing checks to run.
- Measurements and listening-test protocol.
- Raw results and generated artefact locations.
- Interpretation, uncertainty, and unexpected effects.
- Decision: accepted, rejected, inconclusive, or requires another experiment.
- Follow-up work.

A candidate should not be promoted just because the LLM recommends it. It should be promoted because it meets constraints and the available evidence supports the decision.

## 7. Immediate next steps

Keep the first milestone deliberately small. Do not start by building every MCP integration or producing cinematic marketing assets.

1. [ ] Create the repository and commit this roadmap.
2. [ ] Write the first `spec/keyboard.yaml` with objectives, hard constraints, statuses, and units.
3. [ ] Make an initial layout decision list and build the first Ergogen configuration.
4. [ ] Generate and inspect a layout with real switch positions and the intended key count.
5. [ ] Export canonical coordinates in a documented format.
6. [ ] Generate a simple plate and basic case from those coordinates.
7. [ ] Create a small automated check that detects missing keys, collisions, and invalid parameter values.
8. [ ] Only then begin the full KiCad schematic and PCB.

### First milestone definition

**Milestone 1 is complete when one parameter change in the declarative specification reproducibly updates the layout and mechanical outputs, automated checks run, and the generated artefacts are tied to a Git revision.**

After that, expand incrementally into a real KiCad design, firmware, manufacturing release, acoustic experiments, and eventually Blender visualisation and promotional video.
