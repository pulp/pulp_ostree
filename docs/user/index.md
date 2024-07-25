# Welcome to Pulp OSTree

The Pulp OSTree plugin adds support for managing OSTree repositories. In this section,
readers will learn more about the concept of mirroring remote repositories and publishing
them for further client's consumption.

## Features

- **Synchronize** a remote OSTree repository and serve it via Pulp.
- **Import** new OSTree commits to an existing repository.
- **Modify** commits and refs within a published repository.
- **Consume** OSTree content imported to Pulp by leveraging the `ostree` utility.

## Requirements

Usually, it is recommended to instal the following utilities when managing OSTree content:

- [ostree](https://manpages.debian.org/testing/ostree/ostree.1.en.html) - a CLI tool for managing
  versioned filesystem trees locally
- [osbuild-composer](https://github.com/osbuild/osbuild-composer) - an HTTP service for building
  bootable OS disk images
- [composer-cli](https://osbuild.org/docs/user-guide/introduction) - a tool
  for use with a WELDR API server, managing blueprints, or building new images

In this documentation, these utilities are used to demonstrate the way how to create and consume
the OSTree content as well as how they can complement the Pulp's functionality.

For the best user experience, the workflows utilize [Pulp CLI OSTree](https://github.com/pulp/pulp-cli-ostree).
Install the CLI for the OSTree plugin and update its configuration if necessary. It is simple!

```bash
pip install pulp-cli-ostree

pulp config create && pulp config edit  # configure the reference to the running Pulp instance
```
