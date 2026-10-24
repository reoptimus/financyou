#
# This is the server logic of a Shiny web application. You can run the
# application by clicking 'Run App' above.
#

# Define server logic required to draw a histogram
  shinyServer(function(input, output, session) {
    hist<- reactiveVal(0) 
    tab_chrono_r<- reactiveVal(0)
    ######################### chargement user
    observeEvent(input$Testpseudo, {
      # session_pseudo<-"doudoune"
      # passwd<-"[retire]"
      # hist()<-table_proj(session_pseudo,passwd)
      # as.data.frame(hist()$revenu,drop=TRUE)
      hist( table_proj(input$pseudo,input$passwd) )
      # table_proj(session_pseudo,passwd)
      output$top_user<-renderText(
      if ( is.null( hist()) ) { } else { isolate(paste("",input$pseudo, "est connecté(e)")
                                                 ) } )

      if (input$passwd=="" | input$passwd=="0" | is.null(input$passwd)) {
        shinyalert("Oops!", "Tapez votre PassWord", type = "error")
      } else {
        test_pass<-paste0(BDD_List$pseudo,BDD_List$pass)==paste0(input$pseudo,input$passwd)
        if (sum(test_pass)==0) { # user pas retrouve
          if (sum(BDD_List$pseudo==input$pseudo)>0) { # pseudo connu mais pb passwd
            shinyalert("Oops!", "Erreur de PassWord ou Pseudo déja existant", type = "error")
          } else {
            shinyalert("Bienvenu!", "Creation du compte", type = "warning")
            updateTabItems(session, "sidebarID", "Vos_projections") #remet sur l'onglet suivant
            # click("btn_optim") # shinyJS click le bouton optim
            showModal(
              modalDialog(
                title = tagList(
                  renderValueBox({
                    valueBox("Pour commencer"," soyez le(s) bienvenue(s)!", icon=icon("fas fa-users"),color="aqua",width=10)
                  })
                ),
                span(
                  tagList("Voici les résultats de la projection de la situation financière et des projets de Nathalie et Xavier X. pour les 20 prochaines années",br(),br(),
                          "Changez les données pour adapter les résultats à votre profil",br(),br(),
                          "N'hésitez surtout pas à tester différents projets!",br(),"Pour commencer, clickez sur 'Calculer' "),
                  style = "color:black;font-size:16px ; font-weight:bold ;  text-align: center"),
                easyClose = TRUE,
                footer = modalButton("Commencer")
              ) 
            )
          }
        } else { if (sum(test_pass)==1) {#trouve
          shinyalert("Bon retour!", paste0("content de vous revoir ",input$pseudo), type = "info")
          updateTabItems(session, "sidebarID", "Vous") #remet sur l'onglet suivant
         
        }else { #pb plusieur fois meme user
          shinyalert("Oops!", "Probleme technique, veuillez ecrire a contact@financyou.com", type = "error")
        }
        }
        
      }
      
    }, ignoreInit = TRUE)
    ##################################### plot_revenu
    observeEvent( {!is.null(hist())},{
      tab_chrono_r(fct_chrono_flux(horiz,hist()) )
      output$Plot_cash <- renderPlotly({
        Visu_CF(tab_chrono_r(),horiz)
        # Visu_CF(tab_chrono,horiz)
      })
      output$Plot_cumul <- renderPlotly({
        Visu_CF_cumul(tab_chrono_r(),horiz)
      })
      ############ Mise en forme des sliders ##################
      output$slider_sal <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate({
          revenu<-as.data.frame(hist()$revenu[[1]])$Net_imposable
        })
        #setSliderColor("DeepPink", 1)
        sliderInput("slider_sal", "en milliers d'euro:", horiz, 100, as.numeric(revenu)%/%1000, round=1,step=2)
      })
      output$slider_epar <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {if (as.data.frame(hist()$revenu[[1]])$taux_eparg==0) {taux=0} else {taux=as.numeric(as.data.frame(hist()$revenu[[1]])$taux_eparg)%/%1000}
        })
        sliderInput("slider_epar", "en Eur:", 0, 50, taux, round=1,step=1)
      })
      output$slider_evol_sal <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {
          taux<-as.numeric(as.data.frame(hist()$revenu[[1]])$evol_sal)
        })
        sliderInput("slider_evol_sal", "Evolution du salaire annuel en %:", -2, 6, taux*100, round=1,step=0.5)
      })
      output$slider_evol_sal2 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {
          taux<-as.numeric(as.data.frame(hist()$revenu[[1]])$evol_sal2)
        })
        sliderInput("slider_evol_sal2", "Evolution du salaire annuel en %:", -2, 6, taux*100, round=1,step=0.5)
      })
      output$check_box_evol_sal <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {box_evol_sal1<-as.character(as.data.frame(hist()$revenu[[1]])$box_evol_sal)
        })
        radioButtons("check_box_evol_sal", "", choices = list("stable" = 1,
                                                              "evolue comme les revenus" = 2),
                     selected = box_evol_sal1,
                     
                     inline = TRUE, width = NULL)    })
      output$nb_sal <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {nb_sal1<-as.character(as.data.frame(hist()$revenu[[1]])$nb_sal)
        })
        # selectInput("nb_revenu", label=NULL,
        #             choices = list("1","2"),
        #             selected = nb_sal1,
        #             multiple = FALSE)
        radioButtons("nb_sal", "Adultes dans le foyer fiscal?", choices = list("1 adulte" = 1, 
                                                                               "2 adultes" = 2),
                     selected = nb_sal1,
                     inline = TRUE, width = NULL) })
      output$box1 <- renderUI({
        isolate( {
          nb_sal1<-as.numeric(as.data.frame(hist()$revenu[[1]])$nb_sal)
          widthcal=12/nb_sal1
        })
        boxPlusInfo( id="box",
                    taglist=tagList( uiOutput(outputId="metier1"),
                                     uiOutput(outputId="res_retraite1"),
                                     uiOutput(outputId="slider_evol_sal")),
                    width =widthcal,
                    content_num=8)
          })
      output$sal2 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {revenu_21=as.numeric(as.data.frame(hist()$revenu[[1]])$sal2)%/%1000} )
        sliderInput("sal2", "Revenu Net imposable de la 2nd pers.", 0, 100, revenu_21, round=1,step=1)
      })
      output$res_retraite1 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {res_retraite_11<-as.numeric(as.data.frame(hist()$revenu[[1]])$res_retraite1)
        })
        sliderInput("res_retraite1", "Nb d'année avant retraite à taux plein:", 0, horiz, res_retraite_11, round=1,step=1)
      })
      output$res_retraite2 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {res_retraite_21<-as.numeric(as.data.frame(hist()$revenu[[1]])$res_retraite2)
        })
        sliderInput("res_retraite2", "Nb d'année avant retraite à taux plein:", 0, horiz, res_retraite_21, round=1,step=1)
      })
      output$metier1 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {metier11<-as.character(as.data.frame(hist()$revenu[[1]])$metier1)
        })
        selectInput(inputId="metier1", label="Categorie socio-profesionnelle", 
                    choices=tab_retraite$Activite_socio_pro, selected=metier11, 
                    multiple=FALSE)
      })
      output$metier2 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {metier21<-as.character(as.data.frame(hist()$revenu[[1]])$metier2)
        })
        selectInput(inputId="metier2", label="Categorie socio-profesionnelle", choices=tab_retraite$Activite_socio_pro, selected=metier21, multiple=FALSE)
      })
      output$slider_immo <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {immo<-as.numeric(as.data.frame(hist()$fiche[[1]])$Montantbien)%/%1000
        })
        sliderInput("slider_immo", "en milliers d'euro:", horiz, 1000, immo, round=1,step=1)
      })
      output$slider_loyer <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {loyer<-as.data.frame(hist()$fiche[[1]])$Loyer
        })
        sliderInput("slider_loyer", "en euro:", 200, 3000, as.numeric(loyer)%/%12, round=1,step=10)
      })
      output$check_box1 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {proprio<-as.character(as.data.frame(hist()$fiche[[1]])$proprietaire)
        })
        radioButtons("check_box1", "", choices = list("oui" = 1,
                                                      "non" = 2),
                     selected = proprio,
                     inline = TRUE, width = NULL)    })
      output$check_box2 <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {fini_payer<-as.character(as.data.frame(hist()$fiche[[1]])$finipayer)
        })
        radioButtons("check_box2", "Avez vous fini de la payer?", choices = list("oui" = 1, 
                                                                                 "non" = 2),
                     selected = fini_payer,
                     inline = TRUE, width = NULL) })
      output$slider_immo_antot <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {an_tot<-as.data.frame(hist()$fiche[[1]])$an_tot
        })
        sliderInput("slider_immo_antot", "en euro:", 1, 30, an_tot, round=1,step=1)
      })
      output$slider_immo_anrest <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {an_rest<-as.data.frame(hist()$fiche[[1]])$an_rest
        })
        sliderInput("slider_immo_anrest", "en euro:", 1, 30, an_rest, round=1,step=1)
      })
      output$slider_immo_taux <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {t0<-100*as.numeric(as.data.frame(hist()$fiche[[1]])$taux_crd_immo)
        })
        sliderInput("slider_immo_taux", "en %:", 0, 3, t0, round=.1,step=.1)
      })
      output$slider_immo_mens <- renderUI({
        if (input$Testpseudo == 0)
          return()
        isolate( {annui<-(1/12)*as.numeric(as.data.frame(hist()$fiche[[1]])$annui_immo)
        })
        sliderInput("slider_immo_mens", "en eur:", 300, 3000, annui, round=.1,step=.1)
      })
      output$box2 <- renderUI({
              isolate({
                if (hist()$revenu[[1]]$nb_sal==2) {
                  boxPlus(id="box2",title =tags$strong("Revenu Net imposable"),
                          uiOutput(outputId="slider_sal"),uiOutput(outputId="sal2"),
                          width =6,
                          status ="primary",
                          solidHeader = TRUE,
                          collapsible = FALSE,
                          closable=FALSE,
                          enable_sidebar=TRUE,
                          sidebar_content=tagList("Mettez ici le montant annuel net",br()," imposable des deux revenus du foyer",
                                                  br(),
                                                  "tel qu'il apparait sur votre",br()," déclaration d'impôts",
                                                  br(),
                                                  "L'ordre est arbitraire mais",br()," sera conservé dans la suite"),
                          sidebar_width=100) #sidebar_icon="chess"
                } else {
                  boxPlus(id="box2",title =tags$strong("Revenu Net imposable"),
                          uiOutput(outputId="slider_sal"),
                          width =6,
                          status ="primary",
                          solidHeader = FALSE,
                          collapsible = FALSE,
                          closable=FALSE,
                          enable_sidebar=TRUE,
                          sidebar_content=tagList("Mettez ici le montant annuel net",br()," imposable du revenu du foyer",
                                                  br(),
                                                  "tel qu'il apparait sur votre",br()," déclaration d'impôts"),
                          sidebar_width=100,
                          sidebar_icon="fas fa-gear")
                }
              }) })
      isolate( {
        updateNoUiSliderInput(
          session,"slider_ages",value = hist()$fisc[[1]]$age_enf$data[[1]]$age_enf
        )
      })
      isolate( {
        updateSliderTextInput(
          session,
          "pensions",selected = as.data.frame(hist()$fisc[[1]])$pension[[1]]
        )
      })
      isolate( {
        updateTextInput(session, "montant_pension", value = as.data.frame(hist()$fisc[[1]])$mont_pens[[1]]*1
        )
      })
      # affichage de la table
      output$tab_proj <- DT::renderDataTable({
        if (dim(hist()$projets[[1]])[1]==1) {} else {
          df<-as.data.frame(hist()$projets[[1]])[-1,c("nom_projet","andebut","mont_tot_proj")]
          names(df)<-c("nom","début","montant total")
          #df[["Select"]]<-glue::glue('<input type="checkbox" name="selected"  value="{1:nrow(df)}"><br>')
          df[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete"  value="{1:nrow(df)}"><br>')
          MEF_DT(df)
        }
      })
      # affichage du graph des projets enregistres
      output$graph_proj<-renderPlotly({
        # mise en forme des données
        nb_col<-length(hist()$projets[[1]]$chrono_projet_revenu)
        a_plot<-array(0,dim=c(horiz,nb_col))
        depense<-tab_chrono_r()%>%filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses hors projets")%>%select(-type,-sous.type,-sous.type_2)
        nb_conso<-tab_chrono_r()%>%filter(type=="life",sous.type=="part_conso",sous.type_2=="hors projets")%>%select(-type,-sous.type,-sous.type_2)
        conso_pers<-depense/nb_conso
        
        for (i in 1:nb_col ) {
          a<-as.data.frame(hist()$projets[[1]]$chrono_projet_revenu[[i]])[1:horiz]
          b<-as.data.frame(hist()$projets[[1]]$chrono_projet_epar[[i]])[1:horiz]
          c<-as.data.frame(hist()$projets[[1]]$chrono_projet_principal[[i]])[1:horiz]
          d<-as.data.frame(hist()$projets[[1]]$chrono_projet_crd_imp[[i]])[1:horiz]
          e<-as.data.frame(hist()$projets[[1]]$chrono_projet_part_conso[[i]])[1:horiz]*conso_pers
          a_plot[,i]<- t(a+b+c+d+e)
        }
        a_plot<-as.data.frame(a_plot)
        names(a_plot)<-hist()$projets[[1]]$nom_projet
        # constitution graphique
        if (dim(hist()$projets[[1]])[1]==1) {NULL} else {
          Visu_CF_proj(a_plot)
        }
      })
      output$graph_proj_CF<-renderPlotly({
        Visu_CF_avec_proj(tab_chrono_r(),horiz)
        # Visu_CF_avec_proj(tab_chrono,horiz)
      })
      # affichage du graph des plc enregistres
      output$tab_plc <- DT::renderDataTable({
        df_plc<-as.data.frame(hist()$plc[[1]])[-1,c("nom_plc","type","Valeur_t0")]
        if (dim(hist()$plc[[1]])[1]==1) {} else {
          df_plc<-as.data.frame(hist()$plc[[1]])[-1,c("nom_plc","type","Valeur_t0")]
          df_plc[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete_plc"  value="{1:nrow(df_plc)}"><br>')
          MEF_DT(df_plc)
        }
      })
      output$graph_plc<-renderPlot({
        # mise en forme des données
        ########################
        a_plot_brut<-hist()$plc[[1]]$Valeur_t0
        a_plot_brut<-as.data.frame(a_plot_brut,stringsAsFactors = FALSE )
        rownames(a_plot_brut)<-hist()$plc[[1]]$nom_plc
        a_plot_net<-hist()$plc[[1]]$V0_net
        a_plot_net<-as.data.frame(a_plot_net,stringsAsFactors = FALSE )
        rownames(a_plot_net)<-hist()$plc[[1]]$nom_plc
        # constitution graphique
        Visu_CF_plc(a_plot_brut,a_plot_net)
        #######################
      })
      
    }, ignoreInit = TRUE)
    #################################### radio button nb_sal #######
    observeEvent(input$nb_sal,{
      output$box1 <- renderUI({
        isolate( {
          nb_sal1<-as.numeric(as.data.frame(hist()$revenu[[1]])$nb_sal)
          widthcal=12/nb_sal1
        })
        boxPlusInfo(id="box",
          taglist=tagList( uiOutput(outputId="metier1"),
                           uiOutput(outputId="res_retraite1"),
                           uiOutput(outputId="slider_evol_sal")),
          width =widthcal,
          content_num=8)
      })
      # dynamic box revenu
            output$box2 <- renderUI({
              isolate({
                if (input$nb_sal==2) {
                  boxPlus(id="box2",title =tags$strong("Revenu Net imposable"),
                          uiOutput(outputId="slider_sal"),uiOutput(outputId="sal2"),
                          width =6,
                          status ="primary",
                          solidHeader = TRUE,
                          collapsible = FALSE,
                          closable=FALSE,
                          enable_sidebar=TRUE,
                          sidebar_content=tagList("Mettez ici le montant annuel net ",br(),"imposable des deux revenus du foyer",
                                                  br(),
                                                  "tel qu'il apparait sur votre ",br(),"déclaration d'impôts",
                                                  br(),
                                                  "L'ordre est arbitraire mais ",br(),"sera conservé dans la suite"),
                          sidebar_width=100) #sidebar_icon="chess"
                } else {
                  boxPlus(id="box2",title =tags$strong("Revenu Net imposable"),
                          uiOutput(outputId="slider_sal"),
                          width =6,
                          status ="primary",
                          solidHeader = FALSE,
                          collapsible = FALSE,
                          closable=FALSE,
                          enable_sidebar=TRUE,
                          sidebar_content=tagList("Mettez ici le montant annuel net",br()," imposable du revenu du foyer",
                                                  br(),
                                                  "tel qu'il apparait sur votre",br()," déclaration d'impôts"),
                          sidebar_width=100,
                          sidebar_icon="fas fa-gear")
                }
              }) })
    })
    ############################## save data ######
    observeEvent(input$saveBtn1,{
      if (is.null(input$slider_sal)) {} else {
        if (input$nb_sal==1) { # 1 seul adulte
          hist(table_modif2bis(input$pseudo,input$passwd,hist(),input$slider_sal,0,input$slider_epar,input$nb_sal,input$check_box_evol_sal))  
        } else { # 2 adultes
          hist(table_modif2bis(input$pseudo,input$passwd,hist(),input$slider_sal,input$sal2,input$slider_epar,input$nb_sal,input$check_box_evol_sal))
        }
        output$Plot_cash <- renderPlotly({
          tab_chrono<-fct_chrono_flux(horiz,hist())
          Visu_CF(tab_chrono,horiz)
        })
        output$Plot_cumul <- renderPlotly({
          tab_chrono<-fct_chrono_flux(horiz,hist())
          Visu_CF_cumul(tab_chrono,horiz)
        })
      } # test pour savoir si le revenu panel a ete ouvert
      
      if (is.null(input$slider_evol_sal)) {} else {
        if (is.null(input$slider_evol_sal2)) { # 1 seul adulte
          hist(table_modif2ter(input$pseudo,input$passwd,hist(),input$slider_evol_sal,0,input$res_retraite1,horiz,input$metier1,"sans profession"))   
        } else { # 2 adultes
          hist(table_modif2ter(input$pseudo,input$passwd,hist(),input$slider_evol_sal,input$slider_evol_sal2,input$res_retraite1,input$res_retraite2,input$metier1,input$metier2))
        }
        output$Plot_cash <- renderPlotly({
          tab_chrono<-fct_chrono_flux(horiz,hist())
          Visu_CF(tab_chrono,horiz)
        })
        output$Plot_cumul <- renderPlotly({
          tab_chrono<-fct_chrono_flux(horiz,hist())
          Visu_CF_cumul(tab_chrono,horiz)
        })
      } # test pour savoir si le socio_pro panel a ete ouvert
      
      if (is.null(input$check_box1)) {} else {
        if (input$passwd!="" & input$passwd!="0"){
          if  (input$check_box1=='2'){ # locataire
            hist(table_modif2(input$pseudo,input$passwd,hist(),input$slider_loyer,input$check_box1,'1',0,0,0,0,0) )
          } else { #proprio
            if  (input$check_box2=='2'){ # pas fini de payer
              hist(table_modif2(input$pseudo,input$passwd,hist(),0,input$check_box1,input$check_box2,input$slider_immo,input$slider_immo_antot,input$slider_immo_anrest,input$slider_immo_taux,input$slider_immo_mens) )
            } else { # fini de payer
              hist(table_modif2(input$pseudo,input$passwd,hist(),0,input$check_box1,input$check_box2,input$slider_immo,0,0,0,0) )
            }
          }
          tab_chrono<-fct_chrono_flux(horiz,hist())
          output$Plot_cash <- renderPlotly({
            Visu_CF(tab_chrono,horiz)
          })
          output$Plot_cumul <- renderPlotly({
            Visu_CF_cumul(tab_chrono,horiz)
          })
          # updateCollapse(session,"accordion1", open = "Immo")
        }
      } # test pour savoir si le placement panel a ete ouvert
      
      if (is.null(input$slider_ages)) {} else {
        hist(table_modif4(input$pseudo,input$passwd,hist(),input$slider_ages,input$pensions,input$montant_pension) )
      } # test pour savoir si le fisc panel a ete ouvert
      
      # preparation de la ligne immo propre et sauvegarde dans user pour partie plc
      hist(fct_enr_immo2plc(hist()))
      output$graph_plc<-renderPlot({
        # mise en forme des données
        source(file="Data_Log/FCT_A/Visu_CF_plc.R")
        ########################
        a_plot_brut<-hist()$plc[[1]]$Valeur_t0
        a_plot_brut<-as.data.frame(a_plot_brut,stringsAsFactors = FALSE )
        rownames(a_plot_brut)<-hist()$plc[[1]]$nom_plc
        a_plot_net<-hist()$plc[[1]]$V0_net
        a_plot_net<-as.data.frame(a_plot_net,stringsAsFactors = FALSE )
        rownames(a_plot_net)<-hist()$plc[[1]]$nom_plc
        # constitution graphique
        Visu_CF_plc(a_plot_brut,a_plot_net)
        #######################
      })
      tab_chrono_r(fct_chrono_flux(horiz,hist()) )
      output$Plot_cash <- renderPlotly({
        Visu_CF(tab_chrono_r(),horiz)
        # Visu_CF(tab_chrono,horiz)
      })
      output$Plot_cumul <- renderPlotly({
        Visu_CF_cumul(tab_chrono_r(),horiz)
      })
      ###########################
      # enregistrement a distance
      enr_hist(input$pseudo,input$passwd,hist())
      ###########################
    }, ignoreInit = TRUE)
    ######################### Projets #############
    output$lis_deroul_proj <- renderUI({
      if (input$Testpseudo == 0)
        return()
      selectInput(inputId="lis_deroul_proj",
                  label="",
                  choices=c("temps partiel"),
                  selected=NULL, multiple=FALSE)
    })
    ####### suite projets #######
    observeEvent(input$lis_deroul_proj_type,{
      list<-which(as.character(tab2[,9])==as.character(input$lis_deroul_proj_type))
      updateSelectInput(session,"lis_deroul_proj",choices=as.list(as.character(tab2[list,1])),
                        label="choisissez un projet dans la liste")
    }, ignoreInit = TRUE)      
    ####### suite projets #######
    observeEvent(input$lis_deroul_proj, {
      if (is.null(input$lis_deroul_proj)) {output$UI_projets<-NULL} else {
        result_deroul<-input$lis_deroul_proj
        # result_deroul<-"Investissement Pinel"
        list_UI<-tab2[which(tab2[,1]==result_deroul),-1]
        list_UI<-t(t(list_UI))
        # def des labels
        list_UI_args<-list_UI[10:16]
        list_UI_args <- list_UI_args[which(! is.na(list_UI_args)) ]
        list_UI <- intersect(list_UI, as.character(tab1[,1]) )
        label_list<-c()
        for (i in 1:length(list_UI)) {
          list_UI[i]<-which(as.character(tab1[,1])==list_UI[i])
          label_list<-c(label_list,list_UI_args[i])
        }
        list_UI<- as.numeric(list_UI)
        output$UI_projets<-renderUI({
          fluidRow( mapply(varinput_i,list_UI,label_list) )
        })
      }
    }, ignoreInit = TRUE)
    ############### enr projets ####
    observeEvent(input$Btn_enr_projet , {
      req(input$lis_deroul_proj)
      nb_proj<-which(as.character(tab2[,1])==input$lis_deroul_proj)
      if (length(as.data.frame(hist()$projets[[1]])[,1])>lim_nb_proj) { # verif du nombre de projet
        shinyalert("Vous avez atteint la limite du nombre de projet",closeOnEsc = TRUE,
                   type = "warning",showCancelButton = TRUE, showConfirmButton = FALSE,animation = FALSE)
      } else {
        # nb_proj<-14
        num_UI_proj<-which(!is.na(tab2[nb_proj,2:8]))
        list_UI<-c(nb_proj)
        num_UI_proj<-num_UI_proj+1
        Id_UI_proj<-tab2[nb_proj,num_UI_proj]
        Id_UI_proj<-t(t(Id_UI_proj))
        for (i in 1:length(Id_UI_proj)) {
          labeli<-paste0("input$",Id_UI_proj[i])
          list_UI<-c(list_UI,eval(parse(text=labeli)) )
        }
        # mise  a jour de hist()
        # print(list_UI)
        
        hist(table_modif1(input$pseudo,input$passwd,hist(),list_UI,horiz))
        # affichage de la table  recap projet / recalcul tab_chrono / enr.
        output$tab_proj <- DT::renderDataTable({
          if (dim(hist()$projets[[1]])[1]==1) {NULL} else {
            df<-as.data.frame(hist()$projets[[1]])[-1,c("nom_projet","andebut","mont_tot_proj")]
            # df[["Select"]]<-glue::glue('<input type="checkbox" name="selected"  value="{1:nrow(df)}"><br>')
            df[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete"  value="{1:nrow(df)}"><br>')
            MEF_DT(df)
          }
          # enregistrement a distance
          enr_hist(input$pseudo,input$passwd,hist())
        })
        tab_chrono_r( fct_chrono_flux(horiz,hist()) )
        enr_hist(input$pseudo,input$passwd,hist())
      } # if nb proj OK
    }, ignoreInit = TRUE)
    ################ Projets modif liste #############
    observeEvent(input$checked_rows_delete_d, {
      shinyalert("Voulez-vous supprimer ce projet?",closeOnEsc = TRUE,
                 type = "warning",showCancelButton = TRUE, showConfirmButton = TRUE,animation = FALSE,
                 callbackR = function(x) { if(x != FALSE) {
                   # effacer la ligne de hist_
                   isolate({
                     ligne_proj<-(1+as.numeric(input$checked_rows_delete_d))
                     df<-as.data.frame(hist()$projets[[1]])[-ligne_proj,]
                     ligne_plc_proj<-which(hist()$plc_immo[[1]]$ligne_proj==ligne_proj)
                     if (is.integer0(ligne_plc_proj)==FALSE) {
                       df_plc_proj<-as.data.frame(hist()$plc_immo[[1]])[-ligne_plc_proj,]
                     } else {df_plc_proj<-as.data.frame(hist()$plc_immo[[1]])}
                     # enregistrer hist_
                     hist(table_modif1_bis(input$pseudo,input$passwd,hist(),df,df_plc_proj))
                     # enregistrement a distance
                     enr_hist(input$pseudo,input$passwd,hist())
                   })
                   # recreer le table (renderObject)
                   output$tab_proj <- DT::renderDataTable({
                     df<-df[-1,c("nom_projet","andebut","mont_tot_proj")]
                     #df[["Select"]]<-glue::glue('<input type="checkbox" name="selected"  value="{1:nrow(df)}"><br>')
                     df[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete"  value="{1:nrow(df)}"><br>')
                     MEF_DT(df)
                   })
                 }
                   output$graph_proj<-renderPlotly({
                     # mise en forme des données
                     nb_col<-length(hist()$projets[[1]]$chrono_projet_revenu)
                     a_plot<-array(0,dim=c(horiz+1,nb_col))
                     
                     for (i in 1:nb_col ) {
                       a_plot[,i]<- t(as.data.frame(hist()$projets[[1]]$chrono_projet_revenu[[i]])+as.data.frame(hist()$projets[[1]]$chrono_projet_epar[[i]]))
                     }
                     a_plot<-as.data.frame(a_plot)
                     names(a_plot)<-hist()$projets[[1]]$nom_projet
                     # constitution graphique
                     if (dim(hist()$projets[[1]])[1]==1) {NULL} else {
                       Visu_CF_proj(a_plot)
                     }
                   })

                 })
    }, ignoreInit = TRUE)
    ################# plc ############
    output$lis_deroul_plc <- renderUI({
      if (input$Testpseudo == 0)
        return()
      selectInput(inputId="lis_deroul_plc",
                  label="",
                  choices=c("Actions - PEA","ETF - PEA"),
                  selected=NULL, multiple=FALSE)
    })
    ####### suite placements #######
    observeEvent(input$lis_deroul_plc_type,{
      list<-which(as.character(tab2_plc[,23])==as.character(input$lis_deroul_plc_type))
      updateSelectInput(session,"lis_deroul_plc",choices=as.list(as.character(tab2_plc[list,1])),
                        label="choisissez un placement dans la liste")
    }, ignoreInit = TRUE)      
    ####### suite placements #######
    observeEvent(input$lis_deroul_plc, {
      if (is.null(input$lis_deroul_plc)) {output$UI_plcs<-NULL} else {
        #result_deroul<-input$lis_deroul_plc
        # result_deroul<-"PEA"
        list_UI<-tab2_plc[which(tab2_plc[,1]==input$lis_deroul_plc),-1]
        list_UI<-t(t(list_UI))
        # def des labels
        list_UI_args<-list_UI[8:14]
        list_UI_args <- list_UI_args[which(! is.na(list_UI_args)) ]
        list_UI <- intersect(list_UI, as.character(tab1_plc[,1]) )
        label_list<-c()
        for (i in 1:length(list_UI)) {
          list_UI[i]<-which(as.character(tab1_plc[,1])==list_UI[i])
          label_list<-c(label_list,list_UI_args[i])
        }
        list_UI<- as.numeric(list_UI)
        output$UI_plcs<-renderUI({
          fluidRow( mapply(varinput_i_plc,list_UI,label_list) )
        })
      }
    }, ignoreInit = TRUE)
    ################ enr plc ###########
    observeEvent(input$Btn_enr_plc , {
      req(input$lis_deroul_plc)
      nb_plc<-which(as.character(tab2_plc[,1])==input$lis_deroul_plc)
      if (length(as.data.frame(hist()$plc[[1]])[,1])>lim_nb_plc) { # verif du nombre de placements
        shinyalert("Vous avez atteint la limite du nombre de placements",closeOnEsc = TRUE,
                   type = "warning",showCancelButton = TRUE, showConfirmButton = FALSE,animation = FALSE)
      } else {
        # nb_plc<-6
        num_UI_plc<-which(!is.na(tab2_plc[nb_plc,2:8]))
        list_UI<-c(nb_plc)
        num_UI_plc<-num_UI_plc+1
        Id_UI_plc<-tab2_plc[nb_plc,num_UI_plc]
        Id_UI_plc<-t(t(Id_UI_plc))
        for (i in 1:length(Id_UI_plc)) {
          labeli<-paste0("input$",Id_UI_plc[i])
          list_UI<-c(list_UI,eval(parse(text=labeli)) )
        }
        # enregistrement et mise  a jour de hist()
        hist(table_modif5(hist(),list_UI,horiz))
        # affichage de la table  recap projet
        output$tab_plc <- DT::renderDataTable({
          if (dim(hist()$plc[[1]])[1]==1) {NULL} else {
            df_plc<-as.data.frame(hist()$plc[[1]])[-1,c("nom_plc","type","Valeur_t0")]
            df_plc[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete_plc"  value="{1:nrow(df_plc)}"><br>')
            MEF_DT(df_plc)
          }
        } )
        # enregistrement a distance
        tab_chrono_r( fct_chrono_flux(horiz,hist()) )
        output$Plot_cash <- renderPlotly({
          Visu_CF(tab_chrono_r(),horiz)
        })
        output$Plot_cumul <- renderPlotly({
          Visu_CF_cumul(tab_chrono_r(),horiz)
        })
        enr_hist(input$pseudo,input$passwd,hist())
      } # if nb proj OK
    }, ignoreInit = TRUE)
    observeEvent(input$checked_rows_plc, {
      # print(input$checked_rows_plc)
      shinyalert("Voulez-vous supprimer ce placement?",closeOnEsc = TRUE,
                 type = "warning",showCancelButton = TRUE, showConfirmButton = TRUE,animation = FALSE,
                 callbackR = function(x) { if(x != FALSE) {
                   
                   isolate({
                   # effacer la ligne de hist()
                   df_plc<-as.data.frame(hist()$plc[[1]])[-(1+as.numeric(input$checked_rows_plc)),]
                   # df_plc<-as.data.frame(hist_$plc[[1]])[-4,]
                   # enregistrer hist()
                   hist(table_modif5_bis(hist(),df_plc))
                   # enregistrement a distance
                   enr_hist(input$pseudo,input$passwd,hist())
                   })
                   
                   # recreer le table (renderObject)
                   output$tab_plc <- DT::renderDataTable({
                     if (dim(hist()$plc[[1]])[1]==1) {NULL} else {
                       df_plc<-as.data.frame(hist()$plc[[1]])[-1,c("nom_plc","type","Valeur_t0")]
                       df_plc[["Supprimer"]]<-glue::glue('<input type="checkbox" name="delete_plc"  value="{1:nrow(df_plc)}"><br>')
                       MEF_DT(df_plc)
                     }
                   })
                 }
                   
                   output$graph_plc_brut<-renderPlot({
                     # mise en forme des données
                     a_plot<-hist()$plc[[1]]$Valeur_t0
                     a_plot<-as.data.frame(a_plot,stringsAsFactors = FALSE )
                     rownames(a_plot)<-hist()$plc[[1]]$nom_plc
                     # constitution graphique
                     source(file="Data_Log/FCT_A/Visu_CF_plc.R")
                     Visu_CF_plc(a_plot)
                   })
                   output$graph_plc_net<-renderPlot({
                     # mise en forme des données
                     a_plot<-hist()$plc[[1]]$V0_net
                     a_plot<-as.data.frame(a_plot,stringsAsFactors = FALSE )
                     rownames(a_plot)<-hist()$plc[[1]]$nom_plc
                     # constitution graphique
                     source(file="Data_Log/FCT_A/Visu_CF_plc.R")
                     Visu_CF_plc(a_plot)
                   }) # end fct
                 }) # end shiny alert
    }, ignoreInit = TRUE)
    ##################################### fin plc
    observeEvent(input$btn_optim, {
      #### graphique ####
      isolate({
        shinyalert(
          title = "Mise en garde",
          text = "Cette version n'est pas encore complètement vérifiée et calibrée. N'utilisez pas ces résultats pour prendre une décision financière.",
          type = "warning",
          closeOnEsc = TRUE,
          closeOnClickOutside = FALSE,
          showCancelButton = FALSE,
          showConfirmButton = FALSE,
          timer = 7000)
        # utilise le profil de risque user pour optim MOCA
        Mat_result_tot<-MOCAdre(hist(),tab_chrono_r(),horiz,hist()$avers[[1]]$profilRisk,List_Av,numerotation_GSE)
        # Mat_result_tot<-MOCAdre(hist_,tab_chrono,horiz,hist_$avers[[1]]$profilRisk,List_Av,numerotation_GSE)
        Mat_result_proj<-Mat_result_tot[[1]][[1]]
        Mat_result<-Mat_result_tot[[1]][[2]]
        Rdt_liquide_proj<-Mat_result_tot[[2]][[1]]
        Rdt_liquide<-Mat_result_tot[[2]][[2]]
        list_placements_proj<-Mat_result_tot[[3]][[1]]
        list_placements<-Mat_result_tot[[3]][[2]]
        # apply(Mat_result_proj,2,sum)
        
        list_placements_compl<-Mat_result_tot[[4]]

        #### graphique ####
        output$graph_flux_optim<-renderPlotly({
          Graph_optim(Mat_result,list_placements,list_placements_compl)
        })
        output$graph_flux_optim_proj<-renderPlotly({
          Graph_optim(Mat_result_proj,list_placements_proj,list_placements_compl)
        })
        output$graph_quant<-renderPlotly({
           Visu_quant(apply(Rdt_liquide,c(1,3),sum),list_placements,t(apply(Mat_result,2,sum)))
           })
        output$graph_quant_proj<-renderPlotly({
          Visu_quant(apply(Rdt_liquide_proj,c(1,3),sum),list_placements_proj,t(apply(Mat_result_proj,2,sum)))
        })
        output$graph_liquide<-renderPlot({
          Visu_liquide(tab_chrono_r(),limite_endt,"N",list_placements_compl,Rdt_liquide[1,,1])
        })
        output$graph_liquide_proj<-renderPlot({
          Visu_liquide(tab_chrono_r(),limite_endt,"Y",list_placements_compl,Rdt_liquide[1,,1])
        })
      
      })
      #########  KPI ########
      output$KPI1<-renderValueBox({
        valueBox(
          subtitle="Total revenus hors projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),1,"N"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="aqua"
        )
      })
      output$KPI2<-renderValueBox({
        valueBox(
          subtitle="Total revenus avec projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),1,"Y"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="orange"
        )
      })
      output$KPI3<-renderValueBox({
        valueBox(
          subtitle="Total dépenses hors projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),2,"N"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="aqua"
        )
      })
      output$KPI4<-renderValueBox({
        valueBox(
          subtitle="Total dépenses avec projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),2,"Y"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="orange"
        )
      })
      output$KPI5<-renderValueBox({
        valueBox(
          subtitle="Total impôts hors projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),3,"N"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="aqua"
        )
      })
      output$KPI6<-renderValueBox({
        valueBox(
          subtitle="Total impôts avec projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),3,"Y"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="orange"
        )
      })
      output$KPI7<-renderValueBox({
        valueBox(
          subtitle="Max taux endettement hors projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),4,"N"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="aqua"
        )
      })
      output$KPI8<-renderValueBox({
        valueBox(
          subtitle="Max taux endettement avec projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),4,"Y"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="orange"
        )
      })
      output$KPI9<-renderValueBox({
        valueBox(
          subtitle="Min épargne de précaution hors projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),5,"N"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="aqua"
        )
      })
      output$KPI10<-renderValueBox({
        valueBox(
          subtitle="Min épargne de précaution avec projets", #span("Total de vos revenus",style="font-size:12px")
          value=tags$p(KPI(tab_chrono_r(),5,"Y"), style = "font-size: 15px;"), # KPI(tab_chrono,1,"Y")
          icon = icon("credit-card"),width = 12,color="orange"
        )
      })

    }, ignoreInit = TRUE)

    # ######################### MEF switch demarrage
    # observeEvent({!is.null(hist())}, { #switch
    #   isolate( { num_anticip<-as.data.frame(hist()$avers[[1]])$anticip
    #   num_risk<-as.data.frame(hist()$avers[[1]])$profilRisk
    #   
    #   if (num_anticip==1) {
    #     updatePrettySwitch(session, "switch_trend_max", value = TRUE)
    #     updatePrettySwitch(session, "switch_trend_mid", value = FALSE)
    #     updatePrettySwitch(session, "switch_trend_min", value = FALSE)
    #   } else { if (num_anticip==2) {
    #     updatePrettySwitch(session, "switch_trend_max", value = FALSE)
    #     updatePrettySwitch(session, "switch_trend_mid", value = TRUE)
    #     updatePrettySwitch(session, "switch_trend_min", value = FALSE)
    #   } else {
    #     # num_anticip=3
    #     updatePrettySwitch(session, "switch_trend_max", value = FALSE)
    #     updatePrettySwitch(session, "switch_trend_mid", value = FALSE)
    #     updatePrettySwitch(session, "switch_trend_min", value = TRUE)
    #   }
    #   }
    #   
    #   if (num_risk==1) {
    #     updatePrettySwitch(session, "switch_risk_max", value = TRUE)
    #     updatePrettySwitch(session, "switch_risk_mid", value = FALSE)
    #     updatePrettySwitch(session, "switch_risk_min", value = FALSE)
    #   } else { if (num_risk==2) {
    #     updatePrettySwitch(session, "switch_risk_max", value = FALSE)
    #     updatePrettySwitch(session, "switch_risk_mid", value = TRUE)
    #     updatePrettySwitch(session, "switch_risk_min", value = FALSE)
    #   } else {
    #     # num_risk=3
    #     updatePrettySwitch(session, "switch_risk_max", value = FALSE)
    #     updatePrettySwitch(session, "switch_risk_mid", value = FALSE)
    #     updatePrettySwitch(session, "switch_risk_min", value = TRUE)
    #   }
    #   }
    #   }) #end isolate
    # }, ignoreInit = TRUE)
    # 
    # ######################### switch modif ######
    # observeEvent(input$switch_trend_max, {
    #   isolate ({
    #     if (input$switch_trend_max==TRUE) {
    #       hist(enr_switch(hist(),"trend",1))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_trend_mid", value = FALSE)
    #       updatePrettySwitch(session, "switch_trend_min", value = FALSE)
    #     }
    #   })
    # }, ignoreInit = TRUE)
    # observeEvent(input$switch_trend_mid, {
    #   isolate ({
    #     if (input$switch_trend_mid==TRUE) {
    #       hist(enr_switch(hist(),"trend",2))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_trend_max", value = FALSE)
    #       updatePrettySwitch(session, "switch_trend_min", value = FALSE)
    #     } 
    #   })
    # }, ignoreInit = TRUE)
    # observeEvent(input$switch_trend_min, {
    #   isolate ({
    #     if (input$switch_trend_min==TRUE) {
    #       hist(enr_switch(hist(),"trend",3))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_trend_max", value = FALSE)
    #       updatePrettySwitch(session, "switch_trend_mid", value = FALSE)
    #     } 
    #   })
    # }, ignoreInit = TRUE)
    # 
    # observeEvent(input$switch_risk_max, {
    #   isolate ({
    #     if (input$switch_risk_max==TRUE) {
    #       hist(enr_switch(hist(),"risk",1))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_risk_mid", value = FALSE)
    #       updatePrettySwitch(session, "switch_risk_min", value = FALSE)
    #     }
    #   })
    # }, ignoreInit = TRUE)
    # observeEvent(input$switch_risk_mid, {
    #   isolate ({
    #     
    #     if (input$switch_risk_mid==TRUE) {
    #       hist(enr_switch(hist(),"risk",2))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_risk_max", value = FALSE)
    #       updatePrettySwitch(session, "switch_risk_min", value = FALSE)
    #     } 
    #   })
    # }, ignoreInit = TRUE)
    # observeEvent(input$switch_risk_min, {
    #   isolate ({
    #     if (input$switch_risk_min==TRUE) {
    #       hist(enr_switch(hist(),"risk",3))
    #       enr_hist(input$pseudo,input$passwd,hist())
    #       updatePrettySwitch(session, "switch_risk_max", value = FALSE)
    #       updatePrettySwitch(session, "switch_risk_mid", value = FALSE)
    #     } 
    #   })
    # }, ignoreInit = TRUE)

})

