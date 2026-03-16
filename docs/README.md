# PR Sandbox Automation

**This guide is targeted for PR authors to help them create, manage, and**
**troubleshoot automated sandboxes for their PRs.**

## Table of Contents

- [Creating Sandbox](#creating-sandbox)
- [Sandbox Configuration](#sandbox-configuration)
- [Checking Sandbox Logs](#checking-sandbox-logs)
- [Updating Sandbox](#updating-sandbox)
- [Destroying and Recreating Sandbox](#destroying-and-recreating-sandboxes)
- [About the automation app](#about-the-automation-app)
- [Known Issues and Troubleshooting](#known-issues-and-troubleshooting)

## Creating Sandbox

>[!NOTE]
>Automated sandbox provisioning will only work for those PRs whose base
>repo(aka. target repo) has the Github app installed. This is managed by the
>[organization owners or repository admins](https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party#requirements-to-install-a-github-app).
>
>Under the `openedx` org, this automation is installed in the
>[openedx-platform](https://github.com/openedx/openedx-platform) repo as well as
>all the [frontend-app-*](https://github.com/orgs/openedx/repositories?language=&q=frontend-app-&sort=&type=all)
>repos. To ensure that we have enough sandbox hosting resources to support
>active projects, ⚠️  **please check with an Axim engineer before creating new**
>**sandboxes in the `openedx` org.** ⚠️  Thanks!

1. Sandboxes are provisioned with some [default configurations](#default-configurations).
You can also add any [custom configurations](#custom-configuration) for your sandbox
to the PR body as required.

2. Add the `create-sandbox` label to your PR.

3. This should immediately create a new checkrun called `sandbox_deployment`. You
will find this checkrun listed among the other checks, such as unit test checks,
at the bottom of your PR.
![Screenshot of a checkrun entry.](/docs/images/check_run_entry.png)

4. Click on the `sandbox_deployment` checkrun to get real-time updates about the
different stages of the sandbox deployment pipeline.
![Screenshot of a checkrun updates.](/docs/images/check_run_updates_normal.png)

5. The last step of the deployment process is "ArgoCD sync". In this step, all
the LMS/CMS init jobs, such as migrations, are run sequentially in ArgoCD. You will
find the link to the ArgoCD UI specific to your sandbox along with a set of login
credentials posted in the checkrun. You can log in to the ArgoCD UI to check the
logs of the migrations and other init jobs, which will give you a chance to
check and debug any exceptions there.

6. On successful completion of "ArgoCD sync", the `sandbox_deployment` checkrun
is marked as successful, and the LMS and Studio UI links are posted in the
checkrun along with login credentials for a global staff user. The ArgoCD UI
along with the login credentials is also available in the checkrun on
completion, which can be used to check LMS/Studio/worker pod logs.
![Screenshot of a successful deployment.](/docs/images/check_run_success.png)

7. If any of the deployment steps fail, the automation app retries the failed step
again. If it fails again, a link to the detailed log of the failed job will be
posted in checkrun, which can be used by PR authors to debug build
failure issues.

## Sandbox Configuration

### Default Configurations

Based on the base branch(aka. target branch) of a PR, the sandbox automation
tries to determine which named release of Open edX the PR is intended for.
Certain things, such as `OPENEDX_COMMON_VERSION` and the release version of
Tutor and its plugins, are configured based on this.

For a PR to be recognized as targeting a named release, its base branch
should be of the format

    <release-prefix>/<named_release>.<version>

`release/teak.3`, `release/ulmo` are examples of valid names of base branches.

> [!NOTE]
> The automation app supports only the latest named release to be cut upstream.

If a named release cannot be determined from the base branch, then
`OPENEDX_COMMON_VERSION` is set to `master` and the `main` version of Tutor and
its plugins is used. This assumption is applied in order to cover the vast
majority of PRs. The `OPENEDX_COMMON_VERSION` can be
[overridden](#custom-configuration) by the PR author.

### Custom Configuration

#### 1. Tutor Configurations

These are configurations passed directly to tutor and its plugins, such as
`EDX_PLATFORM_REPOSITORY`, `OPENEDX_EXTRA_PIP_REQUIREMENTS`, `SITE_CONFIG` etc.

To override any of those configurations in your sandbox, you can add them
to the PR body in the following format:

    **Settings**

    ```yaml
    EDX_PLATFORM_REPOSITORY: https://github.com/openedx/openedx-platform.git
    EDX_PLATFORM_VERSION: master

    OPENEDX_EXTRA_PIP_REQUIREMENTS:
    - dnspython
    - openedx-scorm-xblock<13.0.0,>=12.0.0

    SITE_CONFIG:
      version: 0
    ```

#### 2. Grove Configurations

The automation app installs a special tutor plugin called [tutor-contrib-grove](https://gitlab.com/opencraft/dev/tutor-contrib-grove/)
for all the sandboxes, which gives a few extra configuration options for things
like the LMS/CMS settings, ENV variables, feature flags, etc.

The available configuration settings are:

- `GROVE_CMS_ENV` - Patches [cms-env](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/cms.env.yml#L35)
- `GROVE_LMS_ENV` - Patches [lms-env](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/lms.env.yml#L40)
- `GROVE_CMS_ENV_FEATURES` - Patches [cms-env-features](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/cms.env.yml#L9)
- `GROVE_LMS_ENV_FEATURES` - Patches [lms-env-features](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/lms.env.yml#L9)
- `GROVE_COMMON_ENV_FEATURES` - Patches common-env-features in [LMS](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/lms.env.yml#L8)
and [CMS](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/cms.env.yml#L8C13-L8C32)
- `GROVE_CMS_PRODUCTION_SETTINGS` - Patches [openedx-cms-production-settings](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/settings/cms/production.py#L17C11-L17C42)
- `GROVE_LMS_PRODUCTION_SETTINGS` - Patches [openedx-lms-production-settings](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/settings/lms/production.py#L32C11-L32C42)
- `GROVE_MFE_LMS_COMMON_SETTINGS` - Patches [mfe-lms-common-settings](https://github.com/overhangio/tutor-mfe/blob/4dfb4e17e50b23d288efeaa1a2c386d8a2cad799/tutormfe/patches/openedx-lms-production-settings#L91)
- `GROVE_COMMON_SETTINGS` - Patches [openedx-common-settings](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/settings/partials/common_all.py#L258C11-L258C34)
- `GROVE_OPENEDX_AUTH` - Patches [openedx-auth](https://github.com/overhangio/tutor/blob/c7df56a8133274d8357ef9395a2347131f5c21df/tutor/templates/apps/openedx/config/partials/auth.yml#L24)

Similar to the other tutor configurations, these can be added to the PR body
in the following format:

    **Settings**

    ```yaml
    GROVE_COMMON_ENV_FEATURES: |
      ASSUME_ZERO_GRADE_IF_ABSENT_FOR_ALL_TESTS: true

    GROVE_LMS_ENV: |
      REGISTRATION_VALIDATION_RATELIMIT: "100/s"
      REGISTRATION_RATELIMIT: "100/s"
      RATELIMIT_RATE: "100/s"

    EDX_PLATFORM_REPOSITORY: https://github.com/openedx/openedx-platform.git
    EDX_PLATFORM_VERSION: master
    ```

> [!IMPORTANT]
> To remove a config value from a sandbox, simply set it to a blank or null value.
> Removing the config completely from the PR body will still cause it to persist
> in the sandbox.
> Ex. `GROVE_COMMON_ENV_FEATURES: ""`

#### 3. Tutor Plugins

These are used to set the release-version/branch of the tutor plugins to be used
with the sandbox. PR authors can add any other tutor plugins that are needed for
the given PR. For example, if a new plugin is developed.

The standard set of tutor plugins that are added and
enabled to all sandboxes are:

- [s3](https://github.com/hastexo/tutor-contrib-s3)
- [drydock](https://github.com/eduNEXT/drydock)
- [tutor-mfe](https://github.com/overhangio/tutor-mfe)
- [tutor-forum](https://github.com/overhangio/tutor-forum)
- [grove-mfes](https://gitlab.com/opencraft/dev/tutor-contrib-grove/-/tree/main/tutorgrove/plugins/mfes?ref_type=heads)
- [grove-config](https://gitlab.com/opencraft/dev/tutor-contrib-grove/-/tree/main/tutorgrove/plugins/config?ref_type=heads)

These plugins cannot be disabled by the PR authors, but they can override the
version of any of these plugins or include a new plugin not in this list by
adding to the PR body the following format:

    **Tutor requirements**

    ```txt
    # override version of default plugin
    pip install git+https://github.com/overhangio/tutor-mfe.git@ulmo

    # install a new plugin
    pip install git+https://github.com/overhangio/tutor-xqueue.git@main
    # enable the new plugin (always required for new plugins)
    tutor plugins enable xqueue

    ```

> [!IMPORTANT]
> If a new plugin is included here, then PR authors must also add the
> `tutor plugins enable <plugin_name>` command to enable that plugin. This is not
> required if overriding the version of one of the existing plugins.

## Checking Sandbox Logs

The sandbox cluster uses [ArgoCD](https://argo-cd.readthedocs.io/en/stable/) to
manage instance deployments. The ArgoCD UI also gives us the ability to access
live pod logs from the applications deployed in the cluster.

To enable PR authors to view the live logs of their sandbox pods, the
automation app posts a sandbox specific link to the ArgoCD UI in the
`sandbox_deployment` checkrun along with a set of login credentials whenever
the image build stages of sandbox deployment are complete and ArgoCD Sync is
initiated. PR authors can use this link to check the logs of the migrations
and other init jobs that are run as part of the sandbox setup process.

> [!TIP]
> The init job pods and the corresponding logs get cleaned-up by Kubernetes pretty
> quickly after execution. If the init jobs logs are of interest, please watch out
> for them when ArgoCD sync starts and check their logs immediately.

The ArgoCD UI link and credentials are also posted after the deployment is
completed successfully. PR authors can log in to the ArgoCD UI anytime to check
the live logs of their sandbox pods.

Logging into ArgoCD UI for the first time, the layout might seem a bit
confusing, with all the resources in the sandbox's namespace (such as PVCs,
config maps, ingress, replica sets, pods, etc.) listed in a hierarchical tree.
![ArgoCD normal layout](/docs/images/argo_cd_normal_layout.png)

If you are interested in only checking the live logs of sandbox pods after
deployment, you can click on the "Group Nodes" button, which consolidates
the hierarchical tree, making it easier to spot the LMS/CMS service resources.
![ArgoCD group nodes layout](/docs/images/argo_cd_group_nodes.png)

To check the logs of any service, click on either the deployment resource or
the replicate set or the pod of that service. This should open up a pop-up with
live manifest and other details for that resource. Click on the "LOGS" tab at
the top to see the live logs rolling.
![ArgoCD CMS service](/docs/images/argo_cd_cms_service.png)

To check the configurations applied to a service:

1. Click on either the deployment resource, the replica set, or the pod of
that service.
2. Scroll down to find the names of the different configmaps as volumes in the
live manifest.
![ArgoCD Volume maps](/docs/images/argo_cd_live_manifest_volumes.png)

3. You can find the corresponding configmaps in the main ArgoCD UI, listed as
resources in the hierarchical tree. You can click on any config map to check
its contents.
![ArgoCD Config maps](/docs/images/argo_cd_configmaps.png)

## Updating Sandbox

1. Add any [custom configurations](#custom-configuration) for your sandbox
to the PR body as required.

2. Like any other checks (such as unit test checks), the `sandbox_deployment`
checkrun can be triggered by pushing a commit to your PR. Even an empty commit
will do if you want to redeploy the sandbox without any other changes in the
PR - such as if you want to update the sandbox settings.

3. Once a new commit is pushed, you should expect a new `sandbox_deployment`
to be created immediately. The steps involved in the update-sandbox pipeline and
the corresponding updates posted in the `sandbox_deployment` checkrun are
exactly the same as the [create sandbox](#creating-sandbox) flow.

> [!NOTE]
> If you push a commit to your PR while the deployment pipeline from your last commit
> is still running, the running pipeline will be cancelled immediately and a new
> deployment pipeline will be started afresh.

## Destroying and Recreating Sandboxes

Removing the `create-sandbox` label from the PR or merging/closing the PR will
immediately trigger a destroy-sandbox pipeline. This will destroy all the
sandbox pods and its namespace from Kubernetes and destroy MySQL/MongoDB
databases and S3 buckets associated with the sandbox. The status of this
pipeline is *not* posted via a checkrun.

Conversely, adding the `create-sandbox` label to the PR or reopening the
PR will trigger the `sandbox_deployment` checkrun and the corresponding
deployment pipelines.

This can be used by PR authors in scenarios, such as when they suspect there
might be some issues related to migration/data corruption and want to
provision a new sandbox from scratch.

1. Remove the `create-sandbox` label from the PR.
2. Wait for about 20 minutes for the destroy-sandbox pipeline to be
executed completely.
3. Add the `create-sandbox` label to provision the sandbox from scratch.

> [!IMPORTANT]
> It is important to wait for at least 20 minutes before adding the
> `create-sandbox` label. Adding the label prematurely will result
> in the destroy-sandbox pipeline being cancelled and sandbox resources being
> partially destroyed, leading to errors when the new sandbox is
> being provisioned.

## About the Automation App

[pr-sandbox-automation](https://github.com/open-craft/pr-sandbox-automation) is
a Python app based on [FastAPI](https://fastapi.tiangolo.com/), which
orchestrates sandbox creation, configuration, and destruction automatically
based on webhook triggers. Further, the [sandbox cluster](https://github.com/open-craft/phd-cluster-template?tab=readme-ov-file#acknowledgments)
uses a bunch of tools for building images and deploying and managing instances,
including [Tutor](https://docs.tutor.edly.io), [Picasso](https://github.com/eduNEXT/picasso),
[DryDock](https://github.com/eduNEXT/drydock), and [ArgoCD](https://argo-cd.readthedocs.io/en/stable/).

The automation app itself is deployed in the same cluster as the sandboxes and
uses [GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps)
to subscribe to various events related to
[pull requests](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request),
[workflow runs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
and [check runs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#check_run).

Based on different pull request events, the app:

1. Creates a new checkrun in the PR
2. Triggers a sequential list of
[workflows](https://github.com/open-craft/phd-cluster-template/tree/main/.github/workflows)
needed to provision a sandbox
3. Post status updates in the checkrun based on the workflow run webhook triggers
4. Triggers the next workflow in the sequential list if the last one reports as
successfully completed
5. Retries a workflow a given number of times if it reports as failed

### Difference Between openedx-platform PRs and MFE PRs

The automation app differentiates two different categories of repos:

1. Forks of the [openedx-platform repo](https://github.com/openedx/openedx-platform).
Sandboxes for PRs from these forks have the deployment branch configured as the
source repo/branch of the PR.
2. Forks for MFEs. Sandboxes for PRs of these forks have the openedx-platform
master branch configured as the deployment branch by default unless overridden
by the PR author. The source repo/branch of the PR is configured as a custom MFE.

> [!IMPORTANT]
> For MFE forks, it's important that the repo name starts with `frontend-app-`.
> Otherwise, the app will treat it as an openedx-platform fork. This assumption
> is based on the naming convention of MFEs.

## Known Issues and Troubleshooting

1. Due to budgetary constraints, a maximum of 30 sandboxes can be active at a given
point in time in the sandbox cluster. If this limit is reached, any new sandbox
creation will fail with the message `Sandbox deployment has been cancelled since
the maximum number of sandboxes are already deployed`. Please ping in the
[#grove-pr-watcher](https://openedx.slack.com/archives/C05519HHZKM) Slack channel
in this case.
2. The destroy sandbox pipeline sometimes fails due to the DigitalOcean's API
related to MySQL being flaky and also due to Kubernetes namespace taking a long
time to delete. In either of these cases, we can end up in an inconsistent state
where some sandbox resources are deleted and some are not. This is only an issue
for PR authors if they are trying to [recreate a sandbox](#destroying-and-recreating-sandboxes).
The "Generating Initial Sandbox Configs" step might fail in this case if the destroy
pipeline had failed earlier. Please ping in the
[#grove-pr-watcher](https://openedx.slack.com/archives/C05519HHZKM) Slack channel
in this case.
3. The automation app posts a "Waiting for status of next steps" message between
deployment steps. This message means that the last step was completed
successfully and the next step has been triggered by the app, but the app is still
waiting for the step to start (since it takes some time for the runners to spin
up and accept the jobs). This intermediate status should not last more than a
minute or two. If you notice the app is stuck in this status for more than
10-15 minutes, it means something has gone wrong. You should trigger a new pipeline
by pushing a commit to your PR.
![Checkrun waiting status](/docs/images/check_run_waiting.png)

> [!TIP]
> If you regularly notice any issue which is not mentioned here, please check
> the list of known/reported [issues in Github](https://github.com/open-craft/pr-sandbox-automation/issues).
> Please feel free to create a new issue there or add comments to an
> existing issue, or, report the issue to
> the [#grove-pr-watcher](https://openedx.slack.com/archives/C05519HHZKM)
> Slack channel.
