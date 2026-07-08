"""
AYON GraphQL query strings, centralized.

Ported from the original api/graphql_query.py's `Query` class. Two changes
from the original:

1. `query_task_type` now requests the task `id` alongside `type` — the
   original query only returned `type`, which made it impossible to map
   results back to a task id (AyonService.get_task_type_map relies on
   this fix; it's what makes Dept Dailies filtering actually work).
2. The original `query_task_type_by_id` is dropped: it referenced an
   undeclared `$taskType` GraphQL variable and a mismatched `task_id`
   Python variable, so it could never have executed successfully, and
   nothing in the codebase called it.

KNOWN INCONSISTENCY (preserved, not "fixed"): `query_versions` queries
`project(code: $project)` while most other queries here use
`project(name: $project)`. Both were present in the original working
code, so rather than guess which is correct against your AYON schema,
this has been left exactly as-is. Worth confirming against your server
schema (introspect `Query.project` args) before relying on either code
path in production.
"""
from __future__ import annotations


class QueryBuilder:
    @staticmethod
    def query_versions(project: str):
        query = """
        query MyQuery($project: String!){
        project(code : $project) {
          versions ( first : 999999999){
            edges {
              node {
                id
                name
                updatedAt
                author
                status
                allAttrib
                isLatest
                projectName
                thumbnailId
                productId
                taskId
                product {
                  name
                  id
                }
              }
            }
          }
        }
        }
        """
        return query, {"project": project}

    @staticmethod
    def query_representations(project: str, version_ids: list[str]):
        query = """
        query MyQuery($project: String!, $versionIds: [String!]!) {
          project(code: $project) {
            representations(versionIds: $versionIds) {
              edges {
                node {
                  versionId
                  allAttrib
                  path
                  name
                  createdAt
                  status
                  updatedAt
                }
              }
            }
          }
        }
        """
        return query, {"project": project, "versionIds": version_ids}

    @staticmethod
    def query_folders(project: str, folder_types: list[str]):
        query = """
        query MyQuery($project: String!, $folderTypes : [String!]!){
        project(code : $project) {
          folders (first : 99999999, folderTypes : $folderTypes){
            edges {
              node {
                id
                name
              }
            }
          }
        }
        }
        """
        return query, {"project": project, "folderTypes": folder_types}

    @staticmethod
    def query_projects():
        query = """
        query MyQuery {
              projects(first: 9999999) {
                edges {
                  node {
                    active
                    name
                    code
                  }
                }
              }
            }
            """
        return query, {}

    @staticmethod
    def query_project_by_name(project: str):
        query = """
        query ProjectQuery($project: String!) {
            project(name: $project) {
                allAttrib
            }
        }
        """
        return query, {"project": project}

    @staticmethod
    def query_versions_by_id(version_ids: list[str], project: str):
        query = """
        query VersionQuery($project: String!, $versionIds:[String!]) {
            project(name:$project){
                versions(first : 9999999, ids: $versionIds) {
                    edges {
                        node {
                            id
                            name
                            updatedAt
                            author
                            status
                            allAttrib
                            isLatest
                            projectName
                            thumbnailId
                            productId
                            taskId
                            product {
                                name
                                id
                            }
                        }
                    }
                }
            }
        }
        """
        return query, {"project": project, "versionIds": version_ids}

    @staticmethod
    def query_all_versions():
        query = """
        query AllVersionsQuery {
            projects {
                edges {
                    node {
                        versions(latestOnly:true) {
                        edges{
                            node {
                                id
                                projectName
                                taskId
                            }
                        }
                      }
                    }
                }
            }
        }
        """
        return query, {}

    @staticmethod
    def query_task_type(task_ids: list[str]):
        """Fixed vs. the original: now returns `id` so results can be
        mapped back to a task id (see AyonService.get_task_type_map)."""
        query = """
        query TaskTypeQuery($taskIds : [String!]){
          projects {
            edges {
              node {
                tasks(ids:$taskIds){
                  edges{
                    node {
                     id
                     type
                    }
                  }
                }
              }
            }
          }
        }
        """
        return query, {"taskIds": task_ids}

    @staticmethod
    def query_sequences(project: str):
        query = """
        query SequenceQuery($project: String!) {
          project(name: $project){
            folders(folderTypes: "Sequence") {
              edges {
                node {
                  name
                  id
                }
              }
            }
          }
        }
        """
        return query, {"project": project}

    @staticmethod
    def children_query_by_parent(project: str, parent_id: str):
        query = """
        query ChildQuery($project: String!, $parentId:String!){
          project(name: $project) {
            folders(parentId:$parentId) {
              edges {
                node {
                  name
                  id
                  }
                }
              }
            }
        }
        """
        return query, {"project": project, "parentId": parent_id}

    @staticmethod
    def version_query_by_folder(project: str, folder_ids: list[str]):
        query = """
        query VersionsQueryByFolder($project:String!, $folderIds:[String!]) {
            project(name: $project){
              versions(folderIds:$folderIds, latestOnly:true){
                edges {
                  node {
                    id
                    name
                    projectName
                    updatedAt
                    author
                    status
                    allAttrib
                    isLatest
                    thumbnailId
                    productId
                    taskId
                    product {
                      name
                      id
                    }
                  }
                }
              }
            }
        }
        """
        return query, {"project": project, "folderIds": folder_ids}

    @staticmethod
    def query_task_activity(project: str, task_id: str):
        query = """
        query ActivityQuery($project:String!, $taskIds:String!){
          project(name: $project){
            task(id:$taskIds){
              activities{
                edges {
                  node {
                    createdAt
                    creationOrder
                    activityType
                    activityData
                    projectName
                    body
                    files {
                      id
                      name
                      size
                      mime
                    }
                  }
                }
              }
            }
          }
        }
        """
        return query, {"project": project, "taskIds": task_id}

    @staticmethod
    def query_version_by_id(project: str, version_id: str):
        query = """
        query Version($project: String!, $versionId: String!){
          project(name:$project){
            version(id:$versionId){
              name
              updatedAt
              author
              status
              thumbnailId
              representations {
                edges{
                  node{
                    id
                    path
                    name
                    allAttrib
                  }
                }
              }
            }
          }
        }
        """
        return query, {"project": project, "versionId": version_id}

    @staticmethod
    def query_comments(project: str, entity_ids: list[str]):
        query = """
        query MyQuery($project: String!, $entityIds: [String!]!) {
          project(code: $project) {
            activities(activityTypes: ["status.change", "comment"], entityIds: $entityIds) {
              edges {
                node {
                  body
                  entityType
                  activityType
                  activityData
                  activityId
                  updatedAt
                  projectName
                  creationOrder
                  origin {
                    id
                  }
                  files {
                    id
                    mime
                    size
                    author
                    name
                  }
                }
              }
            }
          }
        }
        """
        return query, {"project": project, "entityIds": entity_ids}
