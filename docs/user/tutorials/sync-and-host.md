# Mirror and Host Content

In this tutorial, there is demonstrated how one can mirror remote content into a local Pulp
repository.

Users can populate their repositories with content from external sources by syncing a remote
repository. The procedure is as follows: first, create a repository object, then establish a
remote object pointing to the external source, and finally execute a sync task. Upon completion
of the sync task, the content is ready to be promoted/published and becomes visible to end users.

## Create a Repository

Start by creating a new repository named "foo".

```bash
pulp ostree repository create --name foo
```

## Create a Remote

Then, create a remote object that informs Pulp about an external content source.

```bash
pulp ostree remote create --name bar --url https://fixtures.pulpproject.org/ostree/small/
```

Optionally, use the standard Linux wildcards `*`, `?` to include or exclude specific commits from
a remote repository. This might be helpful when there is no need to mirror everything from the
remote repository. Besides that, it reduces the network or storage overhead.

```bash
pulp ostree remote create --name bar-filtered --url https://fixtures.pulpproject.org/ostree/small/ --include-refs "[\"stable\"]" --exclude-refs "[\"raw*\"]"
```

## Sync the Repository

After creating the repository and remote, use these objects to kick off a synchronization task.
This tells Pulp to fetch content from the remote source and add it to the repository.

```bash
pulp ostree repository sync --name foo --remote bar
```

!!! note

    The OSTree plugin currently supports only repositories with the modern `archive` format. The
    repository's config file still uses the historical term `archive-z2` to signify such a format.

## Host Content (Create a Distribution)

To serve the OSTree content from Pulp, the user needs to create a distribution that will host the
associated repository at `${PULP_BASE_ADDR}/pulp/content/<distribution.base_path>`:

```bash
pulp ostree distribution create --name fedora-iot --base-path fedora-iot --repository fedora-iot
```

The content present in the latest repository version is automatically published and accessible by
package managers (e.g., the `ostree` utility).


## Consume the Content

Now, configure a local OSTree repository to consume the content from the Pulp repository.

=== "Script"

    ```bash
    ostree --repo=repo init --mode=archive
    ostree --repo=repo remote --no-gpg-verify add pulpos ${PULP_BASE_ADDR}/pulp/content/fedora-iot

    ostree pull --repo=repo --mirror pulpos:fedora/stable/x86_64/iot --depth=-1
    ostree log --repo=repo fedora/stable/x86_64/iot
    ```

=== "Output"

    ```
    commit 9bbeb2f9961b425b70551b91992e4e3169e7c695f93d99b03e3f2aac463231bf
    Parent:  50aeff7f74c66041ffc9e197887bfd5e427248ff1405e0e61e2cff4d3a1cecc7
    ContentChecksum:  237941566711d062b8b73d0c2823225d59c404d78bf184243c6031fa279e8a1f
    Date:  2021-09-06 15:48:13 +0000
    (no subject)

    commit 50aeff7f74c66041ffc9e197887bfd5e427248ff1405e0e61e2cff4d3a1cecc7
    ContentChecksum:  10155b85154b87675970fd56c4a3b44c4739b486772926ed7463f1c827e7a236
    Date:  2021-09-06 11:35:16 +0000
    (no subject)
    ```

!!! note

    The plugin automatically generates static deltas for a specific subset of commits. Currently,
    the summary file is not being updated after every single change to the repository.

Users are allowed to copy and remove content within repositories. When a new ref is being added or
removed from a repository, all the referenced commits and file objects will be added or removed as
well in order to preserve the integrity of the repository. Visit the guide section to learn more
about particular workflows.
