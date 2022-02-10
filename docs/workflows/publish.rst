.. _publish-workflow:

Publish and Host
================

This section assumes that a user has initialized a repository with OSTree content in it. To do this,
see :doc:`sync` or :doc:`import`.

Host Content (Create a Distribution)
------------------------------------

To serve the OSTree content from Pulp, the user needs to create a distribution that will host the
associated repository at ``${PULP_BASE_ADDR}/pulp/content/<distribution.base_path>``::

    pulp ostree distribution create --name fedora-iot --base-path fedora-iot --repository fedora-iot

The content present in the latest repository version is automatically published and accessible by
package managers (e.g., the ``ostree`` utility).

Now, configure a local OSTree repository and consume the content, like so::

    ostree --repo=repo init --mode=archive
    ostree --repo=repo remote --no-gpg-verify add pulpos ${PULP_BASE_ADDR}/pulp/content/fedora-iot

    ostree pull --repo=repo --mirror pulpos:fedora/stable/x86_64/iot --depth=-1
    ostree log --repo=repo fedora/stable/x86_64/iot

Output::

    commit 9bbeb2f9961b425b70551b91992e4e3169e7c695f93d99b03e3f2aac463231bf
    Parent:  50aeff7f74c66041ffc9e197887bfd5e427248ff1405e0e61e2cff4d3a1cecc7
    ContentChecksum:  237941566711d062b8b73d0c2823225d59c404d78bf184243c6031fa279e8a1f
    Date:  2021-09-06 15:48:13 +0000
    (no subject)

    commit 50aeff7f74c66041ffc9e197887bfd5e427248ff1405e0e61e2cff4d3a1cecc7
    ContentChecksum:  10155b85154b87675970fd56c4a3b44c4739b486772926ed7463f1c827e7a236
    Date:  2021-09-06 11:35:16 +0000
    (no subject)
