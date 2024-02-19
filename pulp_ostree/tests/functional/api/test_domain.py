import pytest
from django.conf import settings

if not settings.DOMAIN_ENABLED:
    pytest.skip("Domains not enabled.", allow_module_level=True)


@pytest.mark.parallel
def test_domains(
    domain_factory,
    ostree_remote_factory,
    ostree_remotes_api_client,
    ostree_repository_factory,
    ostree_repositories_api_client,
    ostree_distribution_factory,
    ostree_distributions_api_client,
):
    domain = domain_factory()
    domain_name = domain.name

    remote = ostree_remote_factory(pulp_domain=domain_name)
    assert domain_name in remote.pulp_href
    result = ostree_remotes_api_client.list(pulp_domain=domain_name)
    assert result.count == 1

    repository = ostree_repository_factory(pulp_domain=domain_name, remote=remote.pulp_href)
    assert domain_name in repository.pulp_href
    result = ostree_repositories_api_client.list(pulp_domain=domain_name)
    assert result.count == 1

    distribution = ostree_distribution_factory(
        pulp_domain=domain_name, repository=repository.pulp_href
    )
    assert domain_name in distribution.pulp_href
    result = ostree_distributions_api_client.list(pulp_domain=domain_name)
    assert result.count == 1
