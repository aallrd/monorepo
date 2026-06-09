pipeline {
  agent none

  stages {
    stage('Validate CI Contract') {
      steps {
        script {
          podTemplate(cloud: 'kubernetes') {
            node(POD_LABEL) {
              checkout scm

              def ci = readJSON(file: 'build/ci/images.json').ci
              def jenkinsConfig = ci.registries.jenkins
              def registryEnv = jenkinsConfig.env as String
              if (!env[registryEnv]) {
                error("${registryEnv} must be set to the external OCI registry for Jenkins")
              }

              ci.jobs.each { jobName, job ->
                if (!ci.images[job.image as String]) {
                  error("Job ${jobName} references unknown image ${job.image}")
                }
              }
            }
          }
        }
      }
    }

    stage('Publish CI Images') {
      steps {
        script {
          def ci
          def gitCommit
          def jenkinsConfig
          def jenkinsRegistry

          podTemplate(cloud: 'kubernetes') {
            node(POD_LABEL) {
              checkout scm

              ci = readJSON(file: 'build/ci/images.json').ci
              gitCommit = env.GIT_COMMIT ?: sh(script: 'git rev-parse HEAD', returnStdout: true).trim()

              jenkinsConfig = ci.registries.jenkins
              def registryEnv = jenkinsConfig.env as String
              jenkinsRegistry = env[registryEnv]
              if (!jenkinsRegistry) {
                error("${registryEnv} must be set to the external OCI registry for Jenkins")
              }
              jenkinsRegistry = jenkinsRegistry.replaceAll('/+$', '')
            }
          }

          def imageRef = { image ->
            return "${jenkinsRegistry}/${image.name}:${gitCommit}"
          }

          def kanikoPodYaml = { ->
            return """
apiVersion: v1
kind: Pod
spec:
  imagePullSecrets:
    - name: ${jenkinsConfig.docker_config_secret}
  containers:
    - name: kaniko
      image: ${jenkinsConfig.kaniko_image}
      command:
        - /busybox/sleep
      args:
        - 99d
      tty: true
      volumeMounts:
        - name: docker-config
          mountPath: /kaniko/.docker
          readOnly: true
  volumes:
    - name: docker-config
      secret:
        secretName: ${jenkinsConfig.docker_config_secret}
        items:
          - key: .dockerconfigjson
            path: config.json
"""
          }

          def branches = [:]

          ci.images.each { imageName, image ->
            def currentImageName = imageName
            def currentImage = image
            branches[currentImageName] = {
              stage("Publish ${currentImage.name}") {
                podTemplate(cloud: jenkinsConfig.kubernetes_cloud, yaml: kanikoPodYaml()) {
                  node(POD_LABEL) {
                    checkout scm
                    container('kaniko') {
                      sh """
/kaniko/executor \\
  --context=dir://${env.WORKSPACE} \\
  --dockerfile=${env.WORKSPACE}/${currentImage.dockerfile} \\
  --destination=${imageRef(currentImage)} \\
  --cache=true \\
  --cache-repo=${imageRef(currentImage)}-cache \\
  --reproducible \\
  --cleanup
"""
                    }
                  }
                }
              }
            }
          }

          parallel branches
        }
      }
    }

    stage('Linux CI Matrix') {
      steps {
        script {
          def ci
          def gitCommit
          def jenkinsConfig
          def jenkinsRegistry

          podTemplate(cloud: 'kubernetes') {
            node(POD_LABEL) {
              checkout scm

              ci = readJSON(file: 'build/ci/images.json').ci
              gitCommit = env.GIT_COMMIT ?: sh(script: 'git rev-parse HEAD', returnStdout: true).trim()

              jenkinsConfig = ci.registries.jenkins
              def registryEnv = jenkinsConfig.env as String
              jenkinsRegistry = env[registryEnv]
              if (!jenkinsRegistry) {
                error("${registryEnv} must be set to the external OCI registry for Jenkins")
              }
              jenkinsRegistry = jenkinsRegistry.replaceAll('/+$', '')
            }
          }

          def imageRef = { image ->
            return "${jenkinsRegistry}/${image.name}:${gitCommit}"
          }

          def buildPodYaml = { image ->
            return """
apiVersion: v1
kind: Pod
spec:
  imagePullSecrets:
    - name: ${jenkinsConfig.docker_config_secret}
  containers:
    - name: build
      image: ${imageRef(image)}
      command:
        - sleep
      args:
        - 99d
      tty: true
"""
          }

          def branches = [:]

          ci.jobs.each { jobName, job ->
            def currentJobName = jobName
            def currentJob = job
            def currentImage = ci.images[currentJob.image as String]
            branches[currentJobName] = {
              stage(currentJob.label as String) {
                podTemplate(cloud: jenkinsConfig.kubernetes_cloud, yaml: buildPodYaml(currentImage)) {
                  node(POD_LABEL) {
                    checkout scm
                    try {
                      container('build') {
                        currentJob.commands.eachWithIndex { command, index ->
                          stage("${currentJobName}: step ${index + 1}") {
                            sh(script: command as String)
                          }
                        }
                      }
                    } finally {
                      if (currentJob.reports?.junit) {
                        junit testResults: currentJob.reports.junit.join(','), allowEmptyResults: false
                      }
                      if (currentJob.artifacts) {
                        archiveArtifacts artifacts: currentJob.artifacts.join(','), allowEmptyArchive: true
                      }
                    }
                  }
                }
              }
            }
          }

          parallel branches
        }
      }
    }
  }
}
