# Import Content

Create a new repository by running:

```bash
pulp ostree repository create --name fedora-iot
```

## Import a Commit

First, build an image representing one OSTree commit and wait until the process finishes:

```bash
echo """name = \"fishy-commit\"
description = \"Fishy OSTree commit\"
version = \"0.0.1\"

[[packages]]
name = \"fish\"
version = \"*\"""" > fishy.toml

sudo composer-cli blueprints push fishy.toml
sudo composer-cli compose start-ostree fishy-commit fedora-iot-commit --ref fedora/stable/x86_64/iot
sudo composer-cli compose status
```

Download the result from the server by issuing:

```bash
sudo composer-cli compose image ${COMPOSER_TASK_UUID}
```

Ensure that the downloaded tarball is readable by Pulp and import it:

```bash
pulp ostree repository import-all --name fedora-iot --file ${IMAGE_TARBALL_C1} --repository_name repo
```

!!! note

    The argument `repository_name` describes the name of an OSTree repository that is contained
    within the tarball. The name of a repository created by `composer-cli` defaults to `repo`.


## Import more Commits

If there is a need to import additional commits, one can do so by attaching new commits to the last
commit in the existing repository:

```bash
echo """name = \"vim-commit\"
description = \"Vim OSTree commit\"
version = \"0.0.2\"

[[packages]]
name = \"vim\"
version = \"*\"""" > vim.toml

sudo composer-cli blueprints push vim.toml
```

!!! note

    Through this step, the reader should have distributed the imported repository to enable the
    `composer-cli` utility to download a parent commit to which more commits are going to be
    attached. Follow `the publish workflow <publish-workflow>` to learn how to distribute a
    repository.


Set the reference to the parent commit, the URL of a Pulp repository to verify the parent against,
and monitor the status of the build:

```bash
sudo composer-cli compose start-ostree vim-commit fedora-iot-commit --ref fedora/stable/x86_64/iot --parent fedora/stable/x86_64/iot --url ${DISTRIBUTION_BASE_URL}
sudo composer-cli compose status
```

Download the result from the server by issuing:

```bash
sudo composer-cli compose image ${TASK_UUID}
```

Import the downloaded tarball into Pulp:

```bash
pulp ostree repository import-commits --name fedora-iot --file ${IMAGE_TARBALL_C2} --repository_name repo --ref fedora/stable/x86_64/iot
```

!!! note

    The OSTree plugin currently supports only repositories with the modern `archive` format. The
    repository's config file still uses the historical term `archive-z2` to signify such a format.

