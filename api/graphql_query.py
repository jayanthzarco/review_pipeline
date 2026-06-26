import requests
import os
import json
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(PROJECT_ROOT + "/config.json", 'r') as conf:
    conf_data = json.load(conf)

BASE_URL = conf_data['AYON_SERVER_URL']
API_KEY = conf_data['AYON_API_KEY']
GRAPHQL_URL = f"{BASE_URL.rstrip('/')}/graphql"


class Query:
    @staticmethod
    def query_versions(project):
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

        variables = {"project": project}
        return query, variables

    @staticmethod
    def query_representations(project, version_ids):
        """

        :param project: str
        :param version_ids: list
        :return:
        """
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

        variables = {
            "project": project,
            "versionIds": version_ids
        }

        return query, variables

    @staticmethod
    def query_folders(project, folder_types):
        """

        :param project: str
        :param folder_types: list
        :return:
        """
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

        variables = {"project": project, "folderTypes": folder_types}
        return query, variables

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
        variables = {}
        return query, variables

    @staticmethod
    def query_versions_by_product(project, product_ids):
        version_query = """
        query MyQuery($project: String!, $productIds: [String!]!){
        project(code : $project) {
          versions (productIds: $productIds, first : 99999999){
            edges {
              node {
                id
                name
                updatedAt
                status
                author
                projectName
                representations {
                    edges {
                        node {
                            path
                            name
                            allAttrib
                        }
                    }
                }
              }
            }
          }
        }
        }
        """
        variables = {
            'project': project,
            'productIds': product_ids

        }
        return version_query, variables

    @staticmethod
    def query_comments(project, entity_ids):
        cmt_query = """
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
        variables = {
            'project': project,
            'entityIds': entity_ids
        }
        return cmt_query, variables

    @staticmethod
    def query_versions_with_activities(project, product_ids):
        pv_query = """
        query PastVersionQuery($project: String!, $productIds: [String!]!) {
          project(code: $project) {
            versions(productIds: $productIds) {
              edges {
                node {
                  id
                  name
                  updatedAt
                  status
                  author
                  version

                  representations {
                    edges {
                      node {
                        path
                        name
                        allAttrib
                      }
                    }
                  }

                  projectName

                  activities(
                    activityTypes: ["status.change", "comment"]
                  ) {
                    edges {
                      node {
                        activityData
                        body
                        updatedAt
                        projectName
                        creationOrder
                        activityType

                        files {
                          id
                          mime
                          name
                          size
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "project": project,
            "productIds": product_ids
        }

        return pv_query, variables

    @staticmethod
    def query_project_by_name(project):
        query = """
        query ProjectQuery($project: String!) {
            project(name: $project) {
                allAttrib           }
                                               }
        """
        variables = {
            "project": project
        }
        return query, variables

    @staticmethod
    def query_versions_by_id(versions_ids, project):
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
        version_variables = {
            "project": project,
            "versionIds": versions_ids
        }
        return query, version_variables

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
        var = {}
        return query, var

    @staticmethod
    def query_task_type(task_ids):
        query = """
        query TaskTypeQuery($taskIds : [String!]){
          projects {
            edges {
              node {
                tasks(ids:$taskIds){
                  edges{
                    node {
                     type
                    }
                  }
                }
              }
            } 
          }
        }
        """
        var = {"taskIds": task_ids}
        return query, var

    @staticmethod
    def query_task_type_by_id(project, task_id):
        query = """
        query TaskType($project: String!, $taskType) {
            project(name:$project) {
            task(id:$task_id){
            taskType
             }
            }
        }
        """
        var = {"project": project, "task_id": task_id}
        return query, var

    @staticmethod
    def query_sequences(project):
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
        variables = {'project': project}
        return query, variables

    @staticmethod
    def children_query_by_parent(project, parent_id):
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
        var = {"project": project, "parentId": parent_id}
        return query, var

    @staticmethod
    def version_query_by_folder(project, folder_ids):
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
        var = {"project": project, "folderIds": folder_ids}
        return query, var

    @staticmethod
    def query_task_activity(project, task_id):
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
        variables = {"project": project, "taskIds": task_id}
        return query, variables

    @staticmethod
    def query_version_by_id(project, version_id):
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
        var = {"project": project, "versionId": version_id}
        return query, var


def run_query(query, variables):
    headers = {
        "X-Api-Key": f"{API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GRAPHQL_URL,
        json={
            "query": query,
            "variables": variables},
        headers=headers
    )

    # DEBUG
    if not response.text.strip():
        raise RuntimeError("Empty response")
    if response.text.startswith("<!DOCTYPE html>"):
        print(" Got HTML -> wrong endpoint")
        print(response.text[:300])
        return
    return response.json()
