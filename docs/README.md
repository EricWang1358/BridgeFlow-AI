# Documentation

- [Setup](setup.md): requirements, local startup and troubleshooting.
- User guides: [English](user-guide.en.md) · [简体中文](user-guide.zh.md).
- [Architecture](architecture.md): components, data flow and approval boundaries.
- [Development](development.md): build, offline tests and sample data.
- [Deployment](deployment.md): self-hosting, portal, instance configuration and guest mode.
- [Limitations](limitations.md): supported scope and known gaps.
- [1.0.0 release notes](releases/1.0.0.md).

The user guides are generated from `plugins/src/client/user-guide.ts`, which also supplies the guide inside the product. Update that source and run `pnpm --dir plugins docs:guide` to keep them in sync.
