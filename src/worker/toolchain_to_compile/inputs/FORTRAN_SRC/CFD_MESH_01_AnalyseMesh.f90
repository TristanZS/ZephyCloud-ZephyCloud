!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Topography Data Transfer                                           #
!######################################################################

PROGRAM     CFD_MESH_01_AnalyseMesh
IMPLICIT    NONE

integer:: arg_status,arg_size,i,i2use,ivect,iptliste,inode2use,existe,imax,ifg,iiii
integer:: ncharlogfile,ncharcode,ncharfolder,ncharthchar,ichar1,ichar2
integer:: ngroups,npts,nele,ibid,ig,ng,nfg,i1,i2,i3,i4,i5,i6,i7,i8,ii1,ii2,ii3,ii,idmax,ipmax,iif,iface,ic,iii,already,ipc,ip
integer,dimension(10)::vect
real:: avancement,rbid,xp1,xp2,xp3,yp1,yp2,yp3,xp,yp
integer,dimension(:),pointer:: bcnums,ipts,igpts
integer,dimension(:,:),pointer:: face2node,ptlist
real,dimension(:),pointer:: xpts,ypts,zpts
real,dimension(:),pointer:: xgpts,ygpts,zgpts

character(len=8),dimension(:),pointer:: bcnames
character(len=5):: frac
character(len=1000):: line,newline
character(len=1000):: code,folder,logfile,thchar
character(len=10000):: arg_content

CALL    get_command_argument (1, arg_content, arg_size, arg_status)
ncharcode = arg_size
code(1:ncharcode) = arg_content(1:arg_size)

CALL    get_command_argument (2, arg_content, arg_size, arg_status)
ncharfolder = arg_size
folder(1:ncharfolder) = arg_content(1:arg_size)

CALL    get_command_argument (3, arg_content, arg_size, arg_status)
ncharlogfile = arg_size
logfile(1:ncharlogfile) = arg_content(1:arg_size)

CALL    get_command_argument (4, arg_content, arg_size, arg_status)
ncharthchar = arg_size
thchar(1:ncharthchar) = arg_content(1:arg_size)

if(logfile(1:ncharlogfile).ne.'NONE')then

	avancement=0.1
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=900)
	read(1,'(a)',end=900,err=900) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
	write(2,'(a)') newline
	close(2)
900	continue

endif

open(1,file=folder(1:ncharfolder)//'/FILES/'//code(1:ncharcode)//'.msh2',status='old',action='read')

read(1,*);read(1,*);read(1,*);read(1,*)
read(1,*) ngroups
allocate(bcnums(ngroups-3))
allocate(bcnames(ngroups-3))
read(1,*);read(1,*)
do i=1,ngroups-3
	read(1,*) ibid,bcnums(i),bcnames(i)
enddo
read(1,*);read(1,*);read(1,*)
read(1,*) npts
allocate(ipts(npts))
allocate(xpts(npts))
allocate(ypts(npts))
allocate(zpts(npts))
ig=0
do i=1,npts
	read(1,*) ipts(i),xpts(i),ypts(i),zpts(i)
	if (zpts(i).lt.1.e-8) then
		ig=ig+1
	endif
enddo
ng=ig
allocate(igpts(ng))
allocate(xgpts(ng))
allocate(ygpts(ng))
allocate(zgpts(ng))
ig=0
do i=1,npts
	if (zpts(i).lt.1.e-8) then
		ig=ig+1
		igpts(ig)=ipts(i)
		xgpts(ig)=xpts(i)
		ygpts(ig)=ypts(i)
		zgpts(ig)=zpts(i)
	endif
enddo
read(1,*);read(1,*)
read(1,*) nele
nfg=0
do i=1,nele
	read(1,*) i1,i2,i3,i4
	if((i2.eq.2).and.(i4.eq.3))then
		nfg=nfg+1
	endif
enddo
do i=1,nele
	backspace(1)
enddo
allocate(face2node(nfg,3))
open(2,file=folder(1:ncharfolder)//'/FILES/'//code(1:ncharcode)//'_facground',status='replace',action='write')
do i=1,nele
	read(1,*) i1,i2,i3,i4
	if((i2.eq.2).and.(i4.eq.3))then
		backspace(1)
		read(1,*) i1,i2,i3,i4,i5,i6,i7,i8
		xp1=xpts(i6)
		yp1=ypts(i6)
		xp2=xpts(i7)
		yp2=ypts(i7)
		xp3=xpts(i8)
		yp3=ypts(i8)
		xp=(xp1+xp2+xp3)/3.
		yp=(yp1+yp2+yp3)/3.
		ii1=-888
		ii2=-888
		ii3=-888
		do ii=1,ng
			if(igpts(ii).eq.i6)then
				ii1=ii-1
			endif
			if(igpts(ii).eq.i7)then
				ii2=ii-1
			endif
			if(igpts(ii).eq.i8)then
				ii3=ii-1
			endif
		enddo
		write(2,*) i1,ii1+1,ii2+1,ii3+1,xp,yp
		face2node(i1,1)=ii1
		face2node(i1,2)=ii2
		face2node(i1,3)=ii3
	endif
enddo

close(1)
close(2)

idmax=-1
do i=1,nfg
	do ii=1,3
		idmax=max(idmax,face2node(i,ii))
	enddo
enddo

if(logfile(1:ncharlogfile).ne.'NONE')then

	avancement=0.4
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=901)
	read(1,'(a)',end=900,err=900) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
	write(2,'(a)') newline
	close(2)
901	continue

endif

idmax=idmax+1

open(2,file=folder(1:ncharfolder)//'/FILES/'//code(1:ncharcode)//'_zsinfo',status='replace',action='write')

do iptliste=0,idmax
	do ivect=1,10
		vect(ivect)=-1
	enddo
	do ifg=1,nfg
		do iii=1,3
			inode2use=face2node(ifg,iii)
			if (inode2use==iptliste) then
				do iiii=1,3
					inode2use=face2node(ifg,iiii)
					if (inode2use.ne.iptliste) then
						do ivect=1,10
							if (vect(ivect)==-1) then
								vect(ivect)=inode2use+1
								EXIT
							else if (vect(ivect)==inode2use+1) then
								EXIT
							endif
						enddo
					endif
				enddo
				EXIT
			endif
		enddo
	enddo
	existe=-1
	imax=0
	do ivect=1,10
		if (vect(ivect).ne.-1) then
			existe=1
			imax=ivect
		endif
	enddo
	if (existe>0) then
		write(2,*) iptliste+1,imax,vect
	endif
enddo

close(2)

if(logfile(1:ncharlogfile).ne.'NONE')then
	avancement=1.
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=902)
	read(1,'(a)',end=902,err=902) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=902)
	write(2,'(a)') newline
	close(2)
902 continue
endif

END PROGRAM CFD_MESH_01_AnalyseMesh
